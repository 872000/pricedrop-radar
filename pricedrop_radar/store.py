"""SQLite price-history store."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

from .fetchers import PricePoint

SCHEMA = """
CREATE TABLE IF NOT EXISTS price_points (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    product   TEXT NOT NULL,
    retailer  TEXT NOT NULL,
    price     REAL NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_product_retailer_ts
    ON price_points (product, retailer, timestamp);
"""


class PriceStore:
    """Append-only price history backed by SQLite."""

    def __init__(self, path: str | Path = "data/prices.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    # -- writes -----------------------------------------------------------
    def record(self, point: PricePoint) -> None:
        self._conn.execute(
            "INSERT INTO price_points (product, retailer, price, timestamp)"
            " VALUES (?, ?, ?, ?)",
            (point.product, point.retailer, point.price,
             point.timestamp.isoformat()),
        )
        self._conn.commit()

    def record_many(self, points: list[PricePoint]) -> None:
        self._conn.executemany(
            "INSERT INTO price_points (product, retailer, price, timestamp)"
            " VALUES (?, ?, ?, ?)",
            [(p.product, p.retailer, p.price, p.timestamp.isoformat())
             for p in points],
        )
        self._conn.commit()

    # -- reads ------------------------------------------------------------
    def _rows(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._conn.execute(query, params).fetchall()

    def history(
        self,
        product: str,
        retailer: str | None = None,
        days: int | None = None,
    ) -> list[PricePoint]:
        query = "SELECT product, retailer, price, timestamp FROM price_points WHERE product = ?"
        params: list = [product]
        if retailer:
            query += " AND retailer = ?"
            params.append(retailer)
        if days is not None:
            cutoff = (dt.datetime.now() - dt.timedelta(days=days)).isoformat()
            query += " AND timestamp >= ?"
            params.append(cutoff)
        query += " ORDER BY timestamp ASC"
        return [
            PricePoint(r["product"], r["retailer"], r["price"],
                       dt.datetime.fromisoformat(r["timestamp"]))
            for r in self._rows(query, tuple(params))
        ]

    def latest(
        self, product: str, retailer: str | None = None
    ) -> PricePoint | None:
        query = "SELECT product, retailer, price, timestamp FROM price_points WHERE product = ?"
        params: list = [product]
        if retailer:
            query += " AND retailer = ?"
            params.append(retailer)
        query += " ORDER BY timestamp DESC LIMIT 1"
        rows = self._rows(query, tuple(params))
        if not rows:
            return None
        r = rows[0]
        return PricePoint(r["product"], r["retailer"], r["price"],
                          dt.datetime.fromisoformat(r["timestamp"]))

    def average(self, product: str, retailer: str | None = None,
                days: int = 30) -> float | None:
        cutoff = (dt.datetime.now() - dt.timedelta(days=days)).isoformat()
        query = ("SELECT AVG(price) AS avg_price FROM price_points "
                 "WHERE product = ? AND timestamp >= ?")
        params: list = [product, cutoff]
        if retailer:
            query += " AND retailer = ?"
            params.append(retailer)
        row = self._rows(query, tuple(params))[0]
        return row["avg_price"] if row["avg_price"] is not None else None

    def all_time_low(
        self, product: str, retailer: str | None = None
    ) -> PricePoint | None:
        query = ("SELECT product, retailer, price, timestamp FROM price_points "
                 "WHERE product = ?")
        params: list = [product]
        if retailer:
            query += " AND retailer = ?"
            params.append(retailer)
        query += " ORDER BY price ASC, timestamp DESC LIMIT 1"
        rows = self._rows(query, tuple(params))
        if not rows:
            return None
        r = rows[0]
        return PricePoint(r["product"], r["retailer"], r["price"],
                          dt.datetime.fromisoformat(r["timestamp"]))

    def products(self) -> list[str]:
        return [r["product"] for r in
                self._rows("SELECT DISTINCT product FROM price_points ORDER BY product")]

    def retailers(self, product: str) -> list[str]:
        return [r["retailer"] for r in
                self._rows("SELECT DISTINCT retailer FROM price_points "
                           "WHERE product = ? ORDER BY retailer", (product,))]

    def count(self) -> int:
        return self._rows("SELECT COUNT(*) AS n FROM price_points")[0]["n"]

    def close(self) -> None:
        self._conn.close()
