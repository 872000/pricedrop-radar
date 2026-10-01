"""Price-history charts rendered with matplotlib."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe rendering
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from .config import WatchedProduct
from .store import PriceStore

_STYLE = {
    "figure.figsize": (9.6, 4.6),
    "figure.dpi": 120,
    "font.family": "DejaVu Sans",
    "axes.facecolor": "#10151d",
    "figure.facecolor": "#10151d",
    "axes.edgecolor": "#3b4a5c",
    "axes.labelcolor": "#d7e0ea",
    "xtick.color": "#8fa0b3",
    "ytick.color": "#8fa0b3",
    "text.color": "#d7e0ea",
    "grid.color": "#223041",
    "grid.alpha": 0.7,
}

_RETAILER_COLORS = ["#4cc9f0", "#f72585", "#80ed99", "#ffd166", "#b388ff"]


def render_product_chart(
    product: WatchedProduct, store: PriceStore, out_path: str | Path
) -> Path:
    """Render one PNG chart per product: one line per retailer + target line."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with plt.rc_context(_STYLE):
        fig, ax = plt.subplots()
        plotted = 0
        for idx, retailer in enumerate(product.retailers):
            points = store.history(product.name, retailer)
            if not points:
                continue
            dates = [p.timestamp for p in points]
            prices = [p.price for p in points]
            color = _RETAILER_COLORS[idx % len(_RETAILER_COLORS)]
            ax.plot(dates, prices, label=retailer, color=color, linewidth=2)
            # mark the lowest point
            low = min(points, key=lambda p: p.price)
            ax.scatter([low.timestamp], [low.price], color=color, s=42, zorder=5)
            plotted += 1

        if plotted:
            ax.axhline(product.target_price, color="#e63946", linestyle="--",
                       linewidth=1.4, label=f"Target ${_fmt(product.target_price)}")

        ax.set_title(f"{product.name} — price history", fontsize=13, pad=12)
        ax.set_xlabel("Date")
        ax.set_ylabel(f"Price ({product.currency})")
        ax.grid(True, linestyle="--")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        fig.autofmt_xdate(rotation=25)
        if plotted:
            ax.legend(loc="best", fontsize=9, framealpha=0.85)
        else:
            ax.text(0.5, 0.5, "No price data yet — run `fetch` first.",
                    ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        fig.savefig(out_path, bbox_inches="tight")
        plt.close(fig)
    return out_path


def _fmt(price: float) -> str:
    return f"{price:,.2f}"
