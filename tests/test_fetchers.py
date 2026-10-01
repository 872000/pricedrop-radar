"""Tests for demo fetchers (offline, deterministic)."""

import datetime as dt

from pricedrop_radar.fetchers import DemoFetcher, LiveFetcher, get_fetcher


def test_demo_price_is_deterministic():
    f = DemoFetcher()
    day = dt.date(2026, 9, 15)
    assert f.price_on("Widget", "amazon", day) == f.price_on("Widget", "amazon", day)


def test_demo_price_varies_by_retailer_and_day():
    f = DemoFetcher()
    day = dt.date(2026, 9, 15)
    other = dt.date(2026, 9, 16)
    prices = {f.price_on("Widget", r, d)
              for r in ("amazon", "walmart") for d in (day, other)}
    assert len(prices) == 4  # all distinct
    assert all(p > 0 for p in prices)


def test_demo_backfill_length_and_order():
    f = DemoFetcher(days_back=10)
    points = f.backfill("Widget", "amazon")
    assert len(points) == 11
    assert all(a.timestamp <= b.timestamp
               for a, b in zip(points, points[1:]))


def test_demo_fetch_returns_price_point():
    point = DemoFetcher().fetch("Widget", "amazon")
    assert point is not None
    assert point.product == "Widget"
    assert point.retailer == "amazon"
    assert point.price > 0


def test_live_fetcher_degrades_gracefully(caplog):
    point = LiveFetcher("amazon").fetch("Widget", "amazon")
    assert point is None
    assert "not configured" in caplog.text


def test_get_fetcher_modes():
    assert isinstance(get_fetcher("amazon", "demo"), DemoFetcher)
    assert isinstance(get_fetcher("amazon", "live"), LiveFetcher)
