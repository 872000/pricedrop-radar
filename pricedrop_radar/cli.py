"""Command-line interface for PriceDrop Radar."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .alerts import evaluate_all
from .charts import render_product_chart
from .config import load_watchlist
from .dashboard import generate_dashboard
from .fetchers import DemoFetcher, get_fetcher, supported_retailers
from .store import PriceStore

log = logging.getLogger("pricedrop_radar")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pricedrop_radar",
        description="Track product prices across retailers and get drop alerts.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--watchlist", default="config/watchlist.json",
                   help="path to watchlist JSON (default: config/watchlist.json)")
    p.add_argument("--db", default="data/prices.db",
                   help="SQLite database path (default: data/prices.db)")
    p.add_argument("--mode", choices=["demo", "live"], default="demo",
                   help="demo = offline synthesized data (default); live degrades gracefully")
    p.add_argument("-v", "--verbose", action="store_true")

    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="fetch current prices and store them")
    f.add_argument("--backfill", action="store_true",
                   help="also generate 60 days of demo history (demo mode only)")

    sub.add_parser("check", help="evaluate alert rules and print alerts")

    c = sub.add_parser("chart", help="render price-history charts")
    c.add_argument("--out", default="charts", help="output dir (default: charts)")

    d = sub.add_parser("dashboard", help="build the HTML dashboard")
    d.add_argument("--out", default="dashboard", help="output dir (default: dashboard)")

    dm = sub.add_parser("demo", help="end-to-end demo: fetch, check, charts, dashboard")
    dm.add_argument("--out", default="demo-output",
                    help="output dir for charts+dashboard (default: demo-output)")
    return p


def cmd_fetch(args: argparse.Namespace) -> int:
    products = load_watchlist(args.watchlist)
    store = PriceStore(args.db)
    fetcher = get_fetcher("demo", args.mode) if args.mode == "demo" else None
    backfilled = 0
    for product in products:
        for retailer in product.retailers:
            if retailer not in supported_retailers() and args.mode == "demo":
                log.warning("unknown retailer %r; skipping", retailer)
                continue
            if args.backfill and args.mode == "demo":
                points = DemoFetcher().backfill(product.name, retailer)
                store.record_many(points)
                backfilled += len(points)
            if args.mode == "demo":
                point = DemoFetcher().fetch(product.name, retailer)
            else:
                point = get_fetcher(retailer, "live").fetch(product.name, retailer)
            if point is None:
                continue
            store.record(point)
            print(f"recorded {product.name} @ {retailer}: ${point.price:,.2f}")
    store.close()
    if backfilled:
        print(f"backfilled {backfilled} historical price points")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    products = load_watchlist(args.watchlist)
    store = PriceStore(args.db)
    alerts = evaluate_all(products, store)
    store.close()
    if not alerts:
        print("No alerts — all prices are above targets. ✅")
        return 0
    for alert in alerts:
        print(alert.format())
    print(f"\n{len(alerts)} alert(s) triggered.")
    return 0


def cmd_chart(args: argparse.Namespace) -> int:
    products = load_watchlist(args.watchlist)
    store = PriceStore(args.db)
    for product in products:
        path = render_product_chart(
            product, store, Path(args.out) / f"{product.name}.png")
        print(f"chart saved: {path}")
    store.close()
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    products = load_watchlist(args.watchlist)
    store = PriceStore(args.db)
    alerts = evaluate_all(products, store)
    index = generate_dashboard(products, store, alerts, args.out)
    store.close()
    print(f"dashboard built: {index}")
    print(f"alerts: {len(alerts)}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Full pipeline on bundled demo data: backfill → fetch → check → dashboard."""
    args.mode = "demo"
    args.backfill = True
    print("== step 1/3: fetching demo price history ==")
    cmd_fetch(args)
    print("\n== step 2/3: evaluating alert rules ==")
    cmd_check(args)
    print("\n== step 3/3: building dashboard ==")
    args.out = str(args.out)
    cmd_dashboard(args)
    print("\nDone! Open the dashboard:")
    print(f"  file://{Path(args.out).resolve() / 'index.html'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    handlers = {
        "fetch": cmd_fetch,
        "check": cmd_check,
        "chart": cmd_chart,
        "dashboard": cmd_dashboard,
        "demo": cmd_demo,
    }
    try:
        return handlers[args.command](args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
