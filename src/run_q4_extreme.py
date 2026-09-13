"""Run and visualize a ten-source outward boundary stress case for Q4."""
import json
import math
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Wedge, FancyArrowPatch

from run_q34_validation import OfflineClient, Source, controller_module

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "q4_extreme_boundary"

def main():
    OUT.mkdir(exist_ok=True)
    sources = []
    # Deliberately non-uniform boundary placement: two dense clusters and
    # several isolated sources, all with radial-outward headings.
    angles = [0.02, 0.16, 0.31, 0.47, 1.72, 2.85, 3.62, 4.58, 5.18, 5.34]
    for i, angle in enumerate(angles):
        pos = np.array([1800 * math.cos(angle), 1800 * math.sin(angle)])
        sources.append(Source(i + 1, pos, 1500.0, True, angle))
    client = OfflineClient(sources, 20260913)
    client.calls_log = []
    original_call = client.call
    def logged_call(path, point=None, channel=None):
        out = original_call(path, point, channel)
        client.calls_log.append({"path": path, "position": client.position.tolist(),
                                 "channel": channel, "result": out})
        return out
    client.call = logged_call
    policy = controller_module(4).PlannedNegativeTour(
        client, controller_module(4).Q4_CONFIG)
    result = policy.run()
    clear_order = []
    for action in client.calls_log:
        if action["path"] == "/clear" and action["result"].get("clear_result") == "success":
            if action["channel"] not in clear_order:
                clear_order.append(action["channel"])
    log = {
        "scenario": "10 directional sources on boundary, all radial outward",
        "sources": [{"channel": s.channel, "position": s.position.tolist(),
                     "reception_radius": s.reception_radius,
                     "heading": s.heading, "directional": s.directional,
                     "cleared": s.cleared} for s in sources],
        "actions": client.calls_log,
        "result": result,
        "cleared": sum(s.cleared for s in sources),
        "total": len(sources),
        "virtual_time_s": client.time,
    }
    (OUT / "q4_extreme_boundary_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    positions = np.array([a["position"] for a in client.calls_log], dtype=float)
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.add_patch(Circle(
        (0, 0), 1800, facecolor="#F5F7F9", edgecolor="#AAB4BF",
        lw=0.8, linestyle=(0, (4, 3)), zorder=0))
    for s in sources:
        ax.add_patch(Wedge(s.position, s.reception_radius,
                           math.degrees(s.heading)-90, math.degrees(s.heading)+90,
                           facecolor="#D55E00", edgecolor="none", alpha=.075))
        ax.add_patch(FancyArrowPatch(s.position, s.position + 140*np.array([math.cos(s.heading), math.sin(s.heading)]),
                                     arrowstyle="-|>", mutation_scale=7, color="#D55E00", lw=.9))
        ax.scatter(*s.position, color="#D55E00", s=24, zorder=9)
        order = clear_order.index(s.channel) + 1 if s.channel in clear_order else None
        if order is not None:
            radial = s.position / np.linalg.norm(s.position)
            label_pos = s.position + 95.0 * radial
            ax.text(label_pos[0], label_pos[1], str(order), color="#26384A",
                    fontsize=6.5, fontweight="bold", ha="center", va="center",
                    bbox={"boxstyle": "circle,pad=0.10", "fc": "white",
                          "ec": "#AAB4BF", "lw": 0.5, "alpha": 0.92}, zorder=10)
    # Collapse repeated stationary logging points and separate the route from
    # the translucent detection sectors with a white halo.
    keep = np.r_[True, np.linalg.norm(np.diff(positions, axis=0), axis=1) > 1e-6]
    route = positions[keep]
    ax.plot(route[:, 0], route[:, 1], color="white", lw=4.2,
            solid_capstyle="round", solid_joinstyle="round", zorder=6)
    ax.plot(route[:, 0], route[:, 1], color="#26384A", lw=1.45,
            solid_capstyle="round", solid_joinstyle="round", zorder=7)
    for i in range(1, len(route), max(1, len(route)//12)):
        ax.annotate("", xy=route[i], xytext=route[i-1],
                    arrowprops={"arrowstyle": "-|>", "color": "#26384A",
                                "lw": 0.8, "mutation_scale": 8}, zorder=8)
    ax.scatter(*route[0], color="#26384A", s=35, zorder=9, label="起点")
    ax.scatter(*route[-1], color="#26384A", marker="*", s=70, zorder=9, label="终点")
    ax.set_aspect("equal"); ax.set_xlim(-3000, 3000); ax.set_ylim(-3000, 3000)
    ax.set_xlabel("x/m"); ax.set_ylabel("y/m")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.08), ncol=2,
              frameon=False, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout(pad=1.0)
    fig.savefig(OUT / "q4_extreme_boundary_trajectory.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / "q4_extreme_boundary_trajectory.pdf", bbox_inches="tight")
    print(json.dumps({"cleared": log["cleared"], "total": log["total"],
                      "virtual_time_s": client.time, "actions": len(client.calls_log)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
