"""Watchlist configuration: JSON watchlists describing products to track."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DROP_PCT = 5.0  # alert when price is X% below the 30-day average


@dataclass
class WatchedProduct:
    """A single product on the watchlist."""

    name: str
    target_price: float
    retailers: list[str] = field(default_factory=list)
    drop_pct: float = DEFAULT_DROP_PCT
    currency: str = "CAD"

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("product 'name' must be a non-empty string")
        if self.target_price <= 0:
            raise ValueError(f"product '{self.name}': 'target_price' must be > 0")
        if not self.retailers:
            raise ValueError(f"product '{self.name}': 'retailers' must not be empty")
        if not (0 < self.drop_pct < 100):
            raise ValueError(
                f"product '{self.name}': 'drop_pct' must be between 0 and 100"
            )
        self.name = self.name.strip()


def _parse_product(raw: dict) -> WatchedProduct:
    if not isinstance(raw, dict):
        raise ValueError(f"each product must be an object, got {type(raw).__name__}")
    try:
        name = raw["name"]
        target_price = float(raw["target_price"])
        retailers = list(raw["retailers"])
    except KeyError as exc:
        raise ValueError(f"product is missing required key: {exc}") from exc
    drop_pct = float(raw.get("drop_pct", DEFAULT_DROP_PCT))
    currency = str(raw.get("currency", "CAD"))
    return WatchedProduct(
        name=name, target_price=target_price, retailers=retailers,
        drop_pct=drop_pct, currency=currency,
    )


def load_watchlist(path: str | Path) -> list[WatchedProduct]:
    """Load and validate a watchlist JSON file.

    Expected shape:
        {
          "products": [
            {"name": "...", "target_price": 999.0,
             "retailers": ["amazon", "bestbuy"],
             "drop_pct": 5.0, "currency": "CAD"}
          ]
        }
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"watchlist not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc

    products = raw.get("products") if isinstance(raw, dict) else None
    if not isinstance(products, list) or not products:
        raise ValueError(f"{path}: 'products' must be a non-empty list")
    return [_parse_product(p) for p in products]
