"""Tests for watchlist config loading and validation."""

import json

import pytest

from pricedrop_radar.config import WatchedProduct, load_watchlist


def _write(tmp_path, payload):
    p = tmp_path / "watchlist.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _valid():
    return {"products": [{
        "name": "Test Widget",
        "target_price": 99.99,
        "retailers": ["amazon", "bestbuy"],
    }]}


def test_load_valid_watchlist(tmp_path):
    products = load_watchlist(_write(tmp_path, _valid()))
    assert len(products) == 1
    p = products[0]
    assert p.name == "Test Widget"
    assert p.target_price == 99.99
    assert p.retailers == ["amazon", "bestbuy"]
    assert p.drop_pct == 5.0  # default
    assert p.currency == "CAD"


def test_load_respects_optional_fields(tmp_path):
    payload = {"products": [{
        "name": "Gadget", "target_price": 10.0, "retailers": ["walmart"],
        "drop_pct": 8.5, "currency": "USD",
    }]}
    (p,) = load_watchlist(_write(tmp_path, payload))
    assert p.drop_pct == 8.5
    assert p.currency == "USD"


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_watchlist(tmp_path / "nope.json")


def test_invalid_json_raises(tmp_path):
    p = tmp_path / "watchlist.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_watchlist(p)


@pytest.mark.parametrize("payload", [
    {"products": []},
    {"products": "nope"},
    {"nope": []},
])
def test_empty_or_malformed_products_raises(tmp_path, payload):
    with pytest.raises(ValueError, match="products"):
        load_watchlist(_write(tmp_path, payload))


def test_missing_required_key_raises(tmp_path):
    payload = {"products": [{"name": "X", "retailers": ["amazon"]}]}
    with pytest.raises(ValueError, match="target_price"):
        load_watchlist(_write(tmp_path, payload))


@pytest.mark.parametrize("kwargs", [
    {"name": "", "target_price": 10.0, "retailers": ["amazon"]},
    {"name": "X", "target_price": 0.0, "retailers": ["amazon"]},
    {"name": "X", "target_price": -5.0, "retailers": ["amazon"]},
    {"name": "X", "target_price": 10.0, "retailers": []},
    {"name": "X", "target_price": 10.0, "retailers": ["amazon"], "drop_pct": 0},
    {"name": "X", "target_price": 10.0, "retailers": ["amazon"], "drop_pct": 100},
])
def test_product_validation(kwargs):
    with pytest.raises(ValueError):
        WatchedProduct(**kwargs)
