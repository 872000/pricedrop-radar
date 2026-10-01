"""End-to-end CLI tests: fetch → check → chart → dashboard on demo data."""

import json

from pricedrop_radar import cli
from pricedrop_radar.config import load_watchlist
from pricedrop_radar.store import PriceStore


def _watchlist(tmp_path):
    p = tmp_path / "watchlist.json"
    p.write_text(json.dumps({"products": [{
        "name": "Test Headphones",
        "target_price": 5000.0,  # deliberately high: no below-target alert
        "retailers": ["amazon", "walmart"],
        "drop_pct": 50.0,        # deliberately high: no drop alert expected either
    }]}), encoding="utf-8")
    return p


def _args(tmp_path, **overrides):
    ns = {
        "watchlist": str(_watchlist(tmp_path)),
        "db": str(tmp_path / "prices.db"),
        "mode": "demo",
        "verbose": False,
        "backfill": True,
        "out": str(tmp_path / "out"),
    }
    ns.update(overrides)
    return type("Args", (), ns)()


def test_demo_pipeline_end_to_end(tmp_path, capsys):
    args = _args(tmp_path)
    assert cli.cmd_demo(args) == 0
    out = capsys.readouterr().out
    assert "fetching" in out.lower() or "recorded" in out.lower()

    store = PriceStore(args.db)
    assert store.count() > 0
    store.close()

    index = tmp_path / "out" / "index.html"
    assert index.exists()
    html = index.read_text(encoding="utf-8")
    assert "Test Headphones" in html
    assert "data:image/png;base64" in html  # embedded chart


def test_check_prints_alerts(tmp_path, capsys):
    args = _args(tmp_path)
    cli.cmd_fetch(args)
    # force an alert: target above every price
    store = PriceStore(args.db)
    store.close()
    assert cli.cmd_check(args) == 0
    out = capsys.readouterr().out
    assert "below_target" in out  # target 5000 is above all demo prices


def test_chart_command(tmp_path, capsys):
    args = _args(tmp_path)
    cli.cmd_fetch(args)
    assert cli.cmd_chart(args) == 0
    pngs = list((tmp_path / "out").glob("*.png"))
    assert len(pngs) == 1
    assert pngs[0].stat().st_size > 0
    capsys.readouterr()


def test_main_rejects_missing_watchlist(tmp_path, capsys):
    rc = cli.main(["--watchlist", str(tmp_path / "nope.json"),
                   "--db", str(tmp_path / "p.db"), "check"])
    assert rc == 1
    assert "error" in capsys.readouterr().err.lower()


def test_bundled_watchlist_loads():
    products = load_watchlist("config/watchlist.json")
    assert len(products) >= 3
