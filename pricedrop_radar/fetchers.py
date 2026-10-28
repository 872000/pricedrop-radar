"""Price fetchers.

Every retailer gets a fetcher. ``demo`` fetchers synthesize realistic price
histories completely offline (seeded, deterministic) so the whole project runs
with zero network access. ``live`` fetchers would query real retailer APIs;
they are intentionally stubbed and degrade gracefully — they log a warning
and return ``None`` rather than crashing the pipeline.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import random
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger("pricedrop_radar")


@dataclass
class PricePoint:
    product: str
    retailer: str
    price: float
    timestamp: dt.datetime


class Fetcher(Protocol):
    def fetch(self, product: str, retailer: str) -> PricePoint | None: ...


# ---------------------------------------------------------------------------
# Demo mode: deterministic, offline, realistic price histories
# ---------------------------------------------------------------------------

DEMO_RETAILERS = ["amazon", "bestbuy", "walmart", "canada-computers"]

_DEMO_BASE_PRICES = {
    "Sony WH-1000XM5 Headphones": 549.99,
    "Apple iPad Air 11\" (M3, 128GB)": 799.00,
    "Dyson V15 Detect": 949.99,
}


def _seed(product: str, retailer: str, day: dt.date) -> int:
    """Deterministic seed so demo data is identical on every run."""
    digest = hashlib.sha256(f"{product}|{retailer}|{day.isoformat()}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _retailer_profile(retailer: str) -> tuple[float, float, int]:
    """Return (base_bias, volatility, promo_period_days) per retailer."""
    return {
        "amazon": (0.98, 0.012, 14),
        "bestbuy": (1.00, 0.010, 21),
        "walmart": (0.97, 0.015, 10),
        "canada-computers": (1.01, 0.011, 28),
    }.get(retailer, (1.00, 0.012, 21))


class DemoFetcher:
    """Offline fetcher that produces realistic, repeatable price data."""

    def __init__(self, days_back: int = 60) -> None:
        self.days_back = days_back

    def base_price(self, product: str) -> float:
        if product in _DEMO_BASE_PRICES:
            return _DEMO_BASE_PRICES[product]
        digest = hashlib.sha256(product.encode()).digest()
        return round(150 + (int.from_bytes(digest[:4], "big") % 900), 2)

    def price_on(self, product: str, retailer: str, day: dt.date) -> float:
        """Deterministic price for a product/retailer on a given day."""
        rng = random.Random(_seed(product, retailer, day))
        base = self.base_price(product)
        bias, vol, promo_period = _retailer_profile(retailer)

        # Slow drift + weekly rhythm + promo cycles + noise
        drift = 1.0 - 0.0012 * ((dt.date.today() - day).days)  # slight decline over time
        weekly = 1.0 + 0.004 * (day.weekday() in (5, 6))
        promo = rng.random() < (7 / promo_period)  # promo week with prob ~ 7/period
        discount = rng.uniform(0.10, 0.22) if promo else 0.0
        noise = rng.gauss(0, vol)

        price = base * bias * drift * weekly * (1 - discount) * (1 + noise)
        return round(max(price, 1.0), 2)

    def fetch(self, product: str, retailer: str) -> PricePoint | None:
        return PricePoint(
            product=product,
            retailer=retailer,
            price=self.price_on(product, retailer, dt.date.today()),
            timestamp=dt.datetime.now(),
        )

    def backfill(self, product: str, retailer: str) -> list[PricePoint]:
        """Generate `days_back` days of history, oldest first."""
        today = dt.date.today()
        points = []
        for offset in range(self.days_back, -1, -1):
            day = today - dt.timedelta(days=offset)
            ts = dt.datetime.combine(day, dt.time(9, 0))
            points.append(
                PricePoint(
                    product=product,
                    retailer=retailer,
                    price=self.price_on(product, retailer, day),
                    timestamp=ts,
                )
            )
        return points


# ---------------------------------------------------------------------------
# Live mode: stubbed, degrades gracefully (no network required to import/run)
# ---------------------------------------------------------------------------

class LiveFetcher:
    """Placeholder for a real retailer scraper/API fetcher.

    In demo mode the app never calls this. If called, it warns and returns
    None instead of raising, so a missing integration can't break the pipeline.
    """

    def __init__(self, retailer: str) -> None:
        self.retailer = retailer

    def fetch(self, product: str, retailer: str) -> PricePoint | None:
        log.warning(
            "live fetching for %r is not configured; skipping %r "
            "(run in demo mode instead)",
            self.retailer, product,
        )
        return None


def get_fetcher(retailer: str, mode: str = "demo") -> Fetcher:
    """Return a demo fetcher, or a live fetcher bound to the given retailer."""
    if mode == "demo":
        return DemoFetcher()
    return LiveFetcher(retailer)


def supported_retailers() -> list[str]:
    """Return the retailers the demo fetcher can generate prices for."""
    return list(DEMO_RETAILERS)
