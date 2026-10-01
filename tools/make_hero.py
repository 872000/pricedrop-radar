"""Generate the docs/hero.png banner programmatically (matplotlib)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

W, H = 16, 5
fig, ax = plt.subplots(figsize=(W, H), dpi=120)
fig.patch.set_facecolor("#0b0f14")
ax.set_facecolor("#0b0f14")
ax.set_xlim(0, 16)
ax.set_ylim(0, 5)
ax.axis("off")

# gradient-ish backdrop bands
for i, (y0, color) in enumerate([(0, "#0d1626"), (2.5, "#141b33")]):
    ax.add_patch(FancyBboxPatch((0, y0), 16, 2.5, boxstyle="round,pad=0.02",
                                facecolor=color, edgecolor="none", alpha=0.9))

# price-drop motif: a jagged declining line with a final plunge
rng = np.random.default_rng(7)
x = np.linspace(9.5, 15.5, 40)
y = 4.2 - 0.055 * (x - 9.5) ** 1.35 - rng.normal(0, 0.07, 40)
y[-6:] -= np.linspace(0, 0.55, 6)
ax.plot(x, y, color="#4cc9f0", linewidth=3.2, alpha=0.95, zorder=3)
ax.scatter([x[-1]], [y[-1]], s=130, color="#f72585", zorder=4, edgecolor="white",
           linewidth=1.2)
# faint grid dots
gx, gy = np.meshgrid(np.linspace(9.5, 15.5, 13), np.linspace(0.6, 4.6, 9))
ax.scatter(gx, gy, s=6, color="#223041", alpha=0.8, zorder=1)

# title + tagline
ax.text(0.7, 3.35, "PriceDrop Radar", fontsize=64, weight="bold",
        color="#f1f5f9", va="center", ha="left",
        fontfamily="DejaVu Sans")
ax.text(0.72, 2.35, "Never overpay again — track prices across retailers\n"
                     "and get alerted the moment they drop.",
        fontsize=20, color="#8fa0b3", va="center", ha="left", linespacing=1.5)

# price-drop badge
badge = FancyBboxPatch((0.7, 0.55), 2.6, 0.95,
                       boxstyle="round,pad=0.08,rounding_size=0.25",
                       facecolor="#12291c", edgecolor="#80ed99", linewidth=1.4)
ax.add_patch(badge)
ax.text(2.0, 1.02, "▼  −18.4%", fontsize=22, weight="bold", color="#80ed99",
        ha="center", va="center")

ax.text(15.3, 0.25, "offline-first · sqlite · matplotlib", fontsize=12,
        color="#5b6b7f", ha="right", va="center")

plt.tight_layout(pad=0.4)
fig.savefig("docs/hero.png", bbox_inches="tight", facecolor="#0b0f14")
print("saved docs/hero.png")
