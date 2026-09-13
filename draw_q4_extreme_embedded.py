"""Standalone Nature-style plot for the Q4 extreme case.

All source and route data are embedded below; no simulator or input files are
needed to draw the figure.
"""
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge, FancyArrowPatch

SOURCES = [
    (i + 1, 1800 * math.cos(2 * math.pi * i / 10),
     1800 * math.sin(2 * math.pi * i / 10), 1500.0,
     2 * math.pi * i / 10, i + 1)
    for i in range(10)
]
# Logged model waypoints (consecutive stationary samples collapsed), in metres.
ROUTE = np.array([
    [0, 0], [708.591, 594.579], [316.369, 869.216], [-160.625, 910.947],
    [-594.579, 708.591], [-869.216, 316.369], [-910.947, -160.625],
    [-708.591, -594.579], [-316.369, -869.216], [160.625, -910.947],
    [594.579, -708.591], [869.216, -316.369], [910.947, 160.625],
    [1850, 0], [1738.431, 632.737], [1417.182, 1189.157],
    [925, 1602.147], [577.332, 1784.459], [321.249, 1821.894],
    [-321.249, 1821.894], [-697.455, 1738.585], [-925, 1602.147],
    [-1417.182, 1189.157], [-1738.431, 632.737], [-1850, 0],
    [-1738.431, -632.737], [-1417.182, -1189.157], [-925, -1602.147],
    [-321.249, -1821.894], [321.249, -1821.894], [925, -1602.147],
    [1417.182, -1189.157], [1738.431, -632.737],
    [1406.562, 927.996], [1551.334, 1023.839], [1470.664, 1053.704],
])

fig, ax = plt.subplots(figsize=(7, 7))
ax.add_patch(Circle((0, 0), 1800, facecolor="#F5F7F9", edgecolor="#AAB4BF",
                    lw=.8, linestyle=(0, (4, 3))))
for _, x, y, radius, heading, order in SOURCES:
    ax.add_patch(Wedge((x, y), radius, math.degrees(heading)-90,
                       math.degrees(heading)+90, facecolor="#D55E00",
                       edgecolor="none", alpha=.075))
    ax.add_patch(FancyArrowPatch((x, y), (x + 140*math.cos(heading),
                      y + 140*math.sin(heading)), arrowstyle="-|>",
                      mutation_scale=7, color="#D55E00", lw=.9))
    ax.scatter(x, y, color="#D55E00", s=24, zorder=9)
    radial = np.array([x, y]) / 1800
    ax.text(x + 95*radial[0], y + 95*radial[1], str(order), ha="center",
            va="center", fontsize=6.5, fontweight="bold", color="#26384A",
            bbox={"boxstyle": "circle,pad=.10", "fc": "white",
                  "ec": "#AAB4BF", "lw": .5, "alpha": .92})
ax.plot(ROUTE[:, 0], ROUTE[:, 1], color="white", lw=4.2, zorder=6)
ax.plot(ROUTE[:, 0], ROUTE[:, 1], color="#26384A", lw=1.45, zorder=7)
ax.scatter(*ROUTE[0], color="#26384A", s=35, label="起点", zorder=10)
ax.scatter(*ROUTE[-1], color="#26384A", marker="*", s=70, label="终点", zorder=10)
ax.set(xlim=(-3000, 3000), ylim=(-3000, 3000), xlabel="x/m", ylabel="y/m")
ax.set_aspect("equal")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.legend(loc="upper center", bbox_to_anchor=(.5, -.08), ncol=2,
          frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig("q4_extreme_boundary_embedded.png", dpi=300, bbox_inches="tight")
fig.savefig("q4_extreme_boundary_embedded.pdf", bbox_inches="tight")
plt.show()
