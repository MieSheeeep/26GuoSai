"""Draw a compact coverage map of the Q3/Q4 test-set source locations."""
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from run_q34_validation import generate_sources  # noqa: E402

OUT = ROOT / "latex" / "figures"
SOURCE_COUNTS = range(10, 17)

def main():
    omni, directed = [], []
    for si, source_count in enumerate(SOURCE_COUNTS):
        for run in range(300):
            for source in generate_sources("q4_mixed", 20260913 + si * 10000 + run,
                                           source_count=source_count):
                (directed if source.directional else omni).append(source.position)
    omni, directed = np.asarray(omni), np.asarray(directed)
    fig, ax = plt.subplots(figsize=(6.0, 5.4))
    ax.add_patch(plt.Circle((0, 0), 1800, facecolor="#F4F7FA", edgecolor="#9AA5B1",
                            linewidth=1.0, linestyle=(0, (3, 3)), zorder=0))
    ax.scatter(omni[:, 0], omni[:, 1], s=8, c="#2A6F97", alpha=.22, label="全向源", rasterized=True)
    ax.scatter(directed[:, 0], directed[:, 1], s=10, c="#B23A48", alpha=.28,
               marker="^", label="定向源", rasterized=True)
    handles = [plt.Line2D([], [], marker="o", linestyle="", color="#2A6F97", markersize=6, label="全向源"),
               plt.Line2D([], [], marker="^", linestyle="", color="#B23A48", markersize=6, label="定向源")]
    ax.legend(handles=handles, frameon=False, loc="upper center", bbox_to_anchor=(.5, -0.08), ncol=2)
    ax.set(xlim=(-2000, 2000), ylim=(-2000, 2000), aspect="equal", xlabel="$x$（m）", ylabel="$y$（m）")
    ax.set_title("问题四 2100 个测试样例的源位置覆盖")
    ax.grid(color="#D9DEE7", linewidth=.55, alpha=.7)
    fig.tight_layout()
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "testset_source_coverage.pdf", bbox_inches="tight")
    fig.savefig(OUT / "testset_source_coverage.png", dpi=240, bbox_inches="tight")
    
if __name__ == "__main__":
    main()
