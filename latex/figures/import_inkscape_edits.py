"""Convert the user's adjusted Inkscape SVG figures for XeLaTeX."""

from pathlib import Path

import subprocess


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "inkscape_export" / "inkscape_openable_figures"
DEST = ROOT / "latex" / "figures"
INKSCAPE = Path(r"E:\Program Files\Inkscape\bin\inkscape.exe")

FIGURES = {
    "problem1_circle_counterexample": "problem1_circle_counterexample_semantic",
    "problem1_wedge_intersection": "problem1_wedge_intersection_semantic",
    "problem1_region": "problem1_region_nature_semantic",
    "problem2_forward_lateral_region": "problem2_forward_lateral_region_semantic",
    "problem2_reception_condition": "problem2_reception_condition_semantic",
}


def main() -> None:
    if not INKSCAPE.is_file():
        raise FileNotFoundError(INKSCAPE)
    for output_stem, source_stem in FIGURES.items():
        source = SOURCE / f"{source_stem}(已调整).svg"
        output = DEST / f"{output_stem}_edited.pdf"
        if not source.is_file():
            raise FileNotFoundError(source)
        subprocess.run(
            [
                str(INKSCAPE),
                str(source),
                "--export-type=pdf",
                f"--export-filename={output}",
                "--export-text-to-path",
            ],
            check=True,
        )
        print(f"{source.name} -> {output.name}")


if __name__ == "__main__":
    main()
