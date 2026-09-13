from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "latex" / "figures"

def main():
    img = mpimg.imread(FIG / "q4_extreme_boundary_trajectory.png")
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.4), gridspec_kw={"wspace": .08})
    left = mpimg.imread(FIG / "testset_source_coverage.png")
    axes[0].imshow(img)
    axes[0].axis("off")
    axes[1].imshow(left)
    axes[1].axis("off")
    fig.text(.25, .035, "（a）非均匀边界极端样例", ha="center", va="center", fontsize=11)
    fig.text(.75, .035, "（b）2100 个测试样例的源位置覆盖", ha="center", va="center", fontsize=11)
    fig.subplots_adjust(bottom=.10, left=.01, right=.99, top=.98, wspace=.04)
    fig.savefig(FIG / "q4_testset_coverage_and_extreme.pdf", bbox_inches="tight")
    fig.savefig(FIG / "q4_testset_coverage_and_extreme.png", dpi=240, bbox_inches="tight")

if __name__ == "__main__":
    main()
