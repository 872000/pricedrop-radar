"""HTML dashboard generator: embeds chart PNGs as base64 + alert feed."""

from __future__ import annotations

import base64
import datetime as dt
from pathlib import Path

from .alerts import Alert
from .charts import render_product_chart
from .config import WatchedProduct
from .store import PriceStore

_DASHBOARD_CSS = """
:root { color-scheme: dark; }
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
       background: #0b0f14; color: #d7e0ea; margin: 0; }
header { background: linear-gradient(135deg, #10233b, #1b1035);
         padding: 32px 24px; border-bottom: 1px solid #223041; }
h1 { margin: 0; font-size: 28px; }
header p { margin: 6px 0 0; color: #8fa0b3; }
main { max-width: 1060px; margin: 0 auto; padding: 24px; }
section { margin-bottom: 36px; }
.alert { background: #101a26; border: 1px solid #223041; border-left: 4px solid #f72585;
         border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; }
.alert.ok { border-left-color: #80ed99; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #1b2634; }
th { color: #8fa0b3; font-weight: 600; text-transform: uppercase; font-size: 12px; }
img.chart { width: 100%; border-radius: 10px; border: 1px solid #223041; }
.card { background: #0e141c; border: 1px solid #223041; border-radius: 12px;
        padding: 18px; margin-bottom: 28px; }
footer { text-align: center; color: #5b6b7f; padding: 24px; font-size: 13px; }
.price-down { color: #80ed99; } .price-up { color: #f72585; }
"""


def _img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _latest_summary(product: WatchedProduct, store: PriceStore) -> str:
    rows = []
    for retailer in product.retailers:
        latest = store.latest(product.name, retailer)
        if latest is None:
            rows.append(
                f"<tr><td>{retailer}</td><td>—</td><td>—</td><td>—</td></tr>")
            continue
        low = store.all_time_low(product.name, retailer)
        avg = store.average(product.name, retailer, days=30)
        low_str = f"${low.price:,.2f}" if low else "—"
        avg_str = f"${avg:,.2f}" if avg else "—"
        marker = " 🏆" if low and latest.price <= low.price else ""
        rows.append(
            f"<tr><td>{retailer}</td><td><strong>${latest.price:,.2f}{marker}</strong></td>"
            f"<td>{avg_str}</td><td>{low_str}</td></tr>")
    return ("\n".join(
        ["<table><tr><th>Retailer</th><th>Latest</th><th>30-day avg</th>"
         "<th>All-time low</th></tr>"] + rows + ["</table>"]))


def generate_dashboard(
    products: list[WatchedProduct],
    store: PriceStore,
    alerts: list[Alert],
    out_dir: str | Path,
) -> Path:
    """Render charts + HTML dashboard into ``out_dir``. Returns index path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_dir = out_dir / "charts"
    chart_dir.mkdir(exist_ok=True)

    cards = []
    for product in products:
        chart_path = render_product_chart(
            product, store, chart_dir / f"{_slug(product.name)}.png")
        cards.append(
            f'<div class="card"><h2>{product.name}</h2>'
            f'<p>Target: <strong>${product.target_price:,.2f}</strong> '
            f'· Drop alert at {product.drop_pct:g}% below 30-day average</p>'
            f'<img class="chart" alt="{product.name} price history" '
            f'src="data:image/png;base64,{_img_b64(chart_path)}" />'
            f"{_latest_summary(product, store)}</div>")

    if alerts:
        alert_html = "\n".join(
            f'<div class="alert">{a.format()}</div>' for a in alerts)
    else:
        alert_html = ('<div class="alert ok">✅ No price-drop alerts right now. '
                      'Everything is above your targets.</div>')

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>PriceDrop Radar — Dashboard</title>
<style>{_DASHBOARD_CSS}</style></head>
<body>
<header><h1>📡 PriceDrop Radar</h1>
<p>Tracking {len(products)} products · generated {now}</p></header>
<main>
<section><h2>🔔 Alerts</h2>{alert_html}</section>
<section><h2>📊 Price history</h2>{''.join(cards)}</section>
</main>
<footer>Built with PriceDrop Radar · demo data, offline-first</footer>
</body></html>"""
    index = out_dir / "index.html"
    index.write_text(html, encoding="utf-8")
    return index


def _slug(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
