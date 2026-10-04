"""Alert rule engine.

Three rule types, evaluated per product against the latest price snapshot:

1. ``below_target``  — latest price at or below the watchlist target price.
2. ``drop_vs_avg``    — latest price >= ``drop_pct``% below the 30-day average.
3. ``all_time_low``   — latest price is the lowest ever recorded (ties count).
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import WatchedProduct
from .store import PriceStore

RULE_BELOW_TARGET = "below_target"
RULE_DROP_VS_AVG = "drop_vs_avg"
RULE_ALL_TIME_LOW = "all_time_low"

EMOJIS = {
    RULE_BELOW_TARGET: "🎯",
    RULE_DROP_VS_AVG: "📉",
    RULE_ALL_TIME_LOW: "🏆",
}


@dataclass
class Alert:
    rule: str
    product: str
    retailer: str
    price: float
    message: str

    def format(self) -> str:
        return f"{EMOJIS.get(self.rule, '🔔')} [{self.rule}] {self.message}"


def _fmt(price: float) -> str:
    return f"${price:,.2f}"


def evaluate_product(product: WatchedProduct, store: PriceStore) -> list[Alert]:
    """Evaluate all rules for one product; returns alerts sorted by rule."""
    alerts: list[Alert] = []
    for retailer in product.retailers:
        latest = store.latest(product.name, retailer)
        if latest is None:
            continue

        # Rule 1: below target price
        if latest.price <= product.target_price:
            alerts.append(Alert(
                rule=RULE_BELOW_TARGET,
                product=product.name,
                retailer=retailer,
                price=latest.price,
                message=(f"{product.name} @ {retailer}: {_fmt(latest.price)} "
                         f"is at/below target {_fmt(product.target_price)}"),
            ))

        # Rule 2: dropped by drop_pct% vs 30-day average
        avg = store.average(product.name, retailer, days=30)
        if avg and avg > 0:
            drop = (avg - latest.price) / avg * 100
            if drop >= product.drop_pct:
                alerts.append(Alert(
                    rule=RULE_DROP_VS_AVG,
                    product=product.name,
                    retailer=retailer,
                    price=latest.price,
                    message=(f"{product.name} @ {retailer}: {_fmt(latest.price)} "
                             f"is {drop:.1f}% below the 30-day average {_fmt(avg)}"),
                ))

        # Rule 3: all-time low
        low = store.all_time_low(product.name, retailer)
        if low is not None and latest.price <= low.price:
            alerts.append(Alert(
                rule=RULE_ALL_TIME_LOW,
                product=product.name,
                retailer=retailer,
                price=latest.price,
                message=(f"{product.name} @ {retailer}: {_fmt(latest.price)} "
                         f"is an all-time low"),
            ))
    return sorted(alerts, key=lambda a: (a.product, a.rule, a.retailer))


def evaluate_all(products: list[WatchedProduct], store: PriceStore) -> list[Alert]:
    """Evaluate alert rules for every watched product; returns all alerts."""
    alerts: list[Alert] = []
    for product in products:
        alerts.extend(evaluate_product(product, store))
    return alerts
