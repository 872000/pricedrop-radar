"""Tests for the alert rule engine."""

import datetime as dt

from pricedrop_radar.alerts import (
    RULE_ALL_TIME_LOW,
    RULE_BELOW_TARGET,
    RULE_DROP_VS_AVG,
    evaluate_product,
)
from pricedrop_radar.config import WatchedProduct
from pricedrop_radar.fetchers import PricePoint
from pricedrop_radar.store import PriceStore


def _seed_history(store, retailer, prices):
    """Record prices so the last one is the latest (1/day, oldest first)."""
    now = dt.datetime.now()
    points = [
        PricePoint("Widget", retailer, price,
                   now - dt.timedelta(days=len(prices) - 1 - i))
        for i, price in enumerate(prices)
    ]
    store.record_many(points)


def test_below_target_alert(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    _seed_history(store, "amazon", [100.0] * 30 + [79.99])
    product = WatchedProduct("Widget", 89.99, ["amazon"])
    alerts = evaluate_product(product, store)
    rules = {a.rule for a in alerts if a.retailer == "amazon"}
    assert RULE_BELOW_TARGET in rules
    store.close()


def test_no_below_target_when_above(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    _seed_history(store, "amazon", [100.0] * 30 + [100.0])
    product = WatchedProduct("Widget", 89.99, ["amazon"])
    alerts = evaluate_product(product, store)
    assert RULE_BELOW_TARGET not in {a.rule for a in alerts}
    store.close()


def test_drop_vs_30d_average_alert(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    _seed_history(store, "amazon", [100.0] * 30 + [90.0])  # 10% below avg
    product = WatchedProduct("Widget", 50.0, ["amazon"], drop_pct=5.0)
    alerts = evaluate_product(product, store)
    assert RULE_DROP_VS_AVG in {a.rule for a in alerts}
    store.close()


def test_small_dip_does_not_alert(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    _seed_history(store, "amazon", [100.0] * 30 + [98.0])  # 2% below avg
    product = WatchedProduct("Widget", 50.0, ["amazon"], drop_pct=5.0)
    alerts = evaluate_product(product, store)
    assert RULE_DROP_VS_AVG not in {a.rule for a in alerts}
    store.close()


def test_all_time_low_alert(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    _seed_history(store, "amazon", [100.0] * 30 + [85.0])
    product = WatchedProduct("Widget", 50.0, ["amazon"])
    alerts = evaluate_product(product, store)
    assert RULE_ALL_TIME_LOW in {a.rule for a in alerts}
    store.close()


def test_no_history_no_alerts(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    product = WatchedProduct("Widget", 89.99, ["amazon"])
    assert evaluate_product(product, store) == []
    store.close()


def test_alert_format_contains_rule_and_price(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    _seed_history(store, "amazon", [100.0] * 30 + [70.0])
    product = WatchedProduct("Widget", 89.99, ["amazon"])
    alerts = evaluate_product(product, store)
    assert alerts
    text = alerts[0].format()
    assert "Widget" in text and "70.00" in text
    store.close()
