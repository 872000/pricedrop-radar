"""Tests for the SQLite price-history store."""

import datetime as dt

from pricedrop_radar.fetchers import PricePoint
from pricedrop_radar.store import PriceStore


def _point(product="Widget", retailer="amazon", price=100.0, days_ago=0):
    return PricePoint(product, retailer, price,
                      dt.datetime.now() - dt.timedelta(days=days_ago))


def test_record_and_latest(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    store.record(_point(price=120.0, days_ago=2))
    store.record(_point(price=99.0, days_ago=0))
    latest = store.latest("Widget", "amazon")
    assert latest is not None and latest.price == 99.0
    store.close()


def test_history_filters_and_orders(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    store.record_many([
        _point(price=100.0, days_ago=10),
        _point(price=110.0, days_ago=5),
        _point(retailer="bestbuy", price=105.0, days_ago=3),
    ])
    hist = store.history("Widget", "amazon")
    assert [p.price for p in hist] == [100.0, 110.0]  # oldest first
    recent = store.history("Widget", days=7)
    assert len(recent) == 2
    store.close()


def test_average_and_all_time_low(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    store.record_many([
        _point(price=100.0, days_ago=29),
        _point(price=90.0, days_ago=20),
        _point(price=110.0, days_ago=40),  # outside 30-day window
    ])
    avg = store.average("Widget", "amazon", days=30)
    assert avg == 95.0
    low = store.all_time_low("Widget", "amazon")
    assert low is not None and low.price == 90.0
    store.close()


def test_empty_store_returns_none(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    assert store.latest("Nothing") is None
    assert store.average("Nothing") is None
    assert store.all_time_low("Nothing") is None
    assert store.history("Nothing") == []
    store.close()


def test_products_and_retailers(tmp_path):
    store = PriceStore(tmp_path / "p.db")
    store.record_many([_point("A", "amazon"), _point("A", "walmart"),
                       _point("B", "amazon")])
    assert store.products() == ["A", "B"]
    assert store.retailers("A") == ["amazon", "walmart"]
    assert store.count() == 3
    store.close()
