from pathlib import Path
import re
import sys


LATEX_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "main.tex",
    "config/packages.tex", "config/layout.tex", "config/commands.tex",
    "chapters/摘要/main.tex", "chapters/问题重述/main.tex",
    "chapters/问题分析/main.tex", "chapters/模型假设/main.tex",
    "chapters/符号说明/main.tex", "chapters/模型评价与推广/main.tex",
    "chapters/参考文献/main.tex", "chapters/附录/main.tex",
    "chapters/问题一/main.tex", "chapters/问题一/问题分析.tex",
    "chapters/问题一/模型建立.tex", "chapters/问题一/算法设计.tex",
    "chapters/问题一/结果分析.tex",
    "chapters/问题二/main.tex", "chapters/问题二/问题分析.tex",
    "chapters/问题二/候选区域.tex", "chapters/问题二/优化模型.tex",
    "chapters/问题二/结果分析.tex",
    "chapters/问题三/main.tex", "chapters/问题三/问题分析.tex",
    "chapters/问题三/搜索策略.tex", "chapters/问题三/算法设计.tex",
    "chapters/问题三/结果分析.tex",
    "chapters/问题四/main.tex", "chapters/问题四/问题分析.tex",
    "chapters/问题四/检测策略.tex", "chapters/问题四/算法设计.tex",
    "chapters/问题四/结果分析.tex",
    "tables/problem3_formal_tests.tex", "tables/problem4_formal_tests.tex",
    "references/references.bib", "code/example.py", "README.md",
]

CONTENT_RULES = {
    "config/packages.tex": [r"listings"],
    "config/commands.tex": [r"modelalgorithm", r"AlgoIn", r"AlgoOut"],
    "chapters/摘要/main.tex": [r"关键词"],
    "chapters/问题一/模型建立.tex": [r"1\^\{\\circ\}", r"定位区域"],
    "chapters/问题一/算法设计.tex": [r"多边形直径"],
    "chapters/问题二/候选区域.tex": [r"\\mathcal\{C\}"],
    "chapters/问题二/优化模型.tex": [r"max"],
    "chapters/问题三/结果分析.tex": [r"清除比例", r"平均定位清除时间", r"problem3_formal_tests"],
    "chapters/问题四/结果分析.tex": [r"清除比例", r"平均定位清除时间", r"problem4_formal_tests"],
    "chapters/附录/main.tex": [r"原文件名"],
}


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

    if failures:
        print("FAIL: missing files or required content:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("PASS: LaTeX template structure and required content are complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
