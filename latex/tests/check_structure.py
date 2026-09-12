from pathlib import Path
import re
import sys


LATEX_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "main.tex",
    "config/packages.tex", "config/layout.tex", "config/commands.tex",
    "chapters/摘要/main.tex", "chapters/问题重述/main.tex",
    "chapters/模型假设/main.tex",
    "chapters/符号说明/main.tex", "chapters/模型评价与推广/main.tex",
    "chapters/参考文献/main.tex", "chapters/附录/main.tex",
    "chapters/问题一/main.tex", "chapters/问题二/main.tex",
    "chapters/问题三/main.tex", "chapters/问题四/main.tex",
    "references/references.bib", "code/example.py", "README.md",
]

CONTENT_RULES = {
    "config/packages.tex": [r"listings"],
    "config/commands.tex": [r"modelalgorithm", r"AlgoIn", r"AlgoOut"],
    "chapters/摘要/main.tex": [r"关键词"],
    "chapters/问题一/main.tex": [r"1\^\{\\circ\}", r"定位区域", r"多边形直径"],
    "chapters/问题二/main.tex": [r"\\mathcal\{C\}", r"max"],
    "chapters/问题三/main.tex": [r"清除比例", r"平均定位清除时间", r"正式测试结果"],
    "chapters/问题四/main.tex": [r"清除比例", r"平均定位清除时间", r"正式测试结果"],
    "chapters/附录/main.tex": [r"原文件名"],
}

PROBLEM_CHAPTERS = [
    "chapters/问题一/main.tex",
    "chapters/问题二/main.tex",
    "chapters/问题三/main.tex",
    "chapters/问题四/main.tex",
]

PROBLEM_SECTION_ORDER = [
    r"\\subsection\{问题分析\}",
    r"\\subsection\{模型建立[^}]*\}",
    r"\\subsection\{模型求解[^}]*\}",
    r"\\subsection\{结果分析[^}]*\}",
    r"\\subsection\{结论\}",
]


def main() -> int:
    failures = [path for path in REQUIRED_FILES if not (LATEX_ROOT / path).is_file()]
    for relative_path, patterns in CONTENT_RULES.items():
        file_path = LATEX_ROOT / relative_path
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8")
        failures.extend(
            f"{relative_path} lacks pattern: {pattern}"
            for pattern in patterns
            if re.search(pattern, content) is None
        )

    packages_path = LATEX_ROOT / "config/packages.tex"
    if packages_path.is_file() and "algorithm2e" in packages_path.read_text(encoding="utf-8"):
        failures.append("config/packages.tex must not depend on unavailable algorithm2e")

    main_path = LATEX_ROOT / "main.tex"
    if main_path.is_file():
        main_content = main_path.read_text(encoding="utf-8")
        if "chapters/问题分析/main" in main_content:
            failures.append("main.tex must not include a standalone problem-analysis chapter")

    standalone_analysis = LATEX_ROOT / "chapters/问题分析/main.tex"
    if standalone_analysis.exists():
        failures.append("chapters/问题分析/main.tex must be removed after migration")

    for relative_path in PROBLEM_CHAPTERS:
        chapter_path = LATEX_ROOT / relative_path
        if not chapter_path.is_file():
            continue
        chapter_content = chapter_path.read_text(encoding="utf-8")
        positions = []
        for pattern in PROBLEM_SECTION_ORDER:
            match = re.search(pattern, chapter_content)
            if match is None:
                failures.append(f"{relative_path} lacks ordered section: {pattern}")
                break
            positions.append(match.start())
        if len(positions) == len(PROBLEM_SECTION_ORDER) and positions != sorted(positions):
            failures.append(f"{relative_path} does not follow the C023 section order")

    chapters_root = LATEX_ROOT / "chapters"
    if chapters_root.is_dir():
        for chapter_dir in (path for path in chapters_root.iterdir() if path.is_dir()):
            tex_files = sorted(path.name for path in chapter_dir.glob("*.tex"))
            if tex_files != ["main.tex"]:
                failures.append(
                    f"{chapter_dir.relative_to(LATEX_ROOT)} must contain only main.tex; found {tex_files}"
                )

    if failures:
        print("FAIL: missing files or required content:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("PASS: LaTeX template structure and required content are complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
