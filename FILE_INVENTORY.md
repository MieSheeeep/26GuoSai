# 文件整理清单

论文电子版入口为 `latex/main.tex`，成品为 `latex/main.pdf`；AI 工具使用详情单独由 `latex/AI工具使用详情.tex` 编译。图形编辑以 `inkscape_export/inkscape_openable_figures/*(已调整).svg` 为准，论文中的五张对应 PDF 由 `latex/figures/import_inkscape_edits.py` 导入。

## 本次已清理

- `latex/build-preview/`、Python 缓存与 pytest 缓存：可再生成的预览、缓存文件。
- `latex/figures/generated_references/`：其中八张 PNG 与 `inkscape_export/image_generated_references_png/` 中的文件逐字节相同；参照稿保留在后者。
- `latex/figures/` 中旧版几何图的十份重复副本：同内容文件保留在 `inkscape_export/`；正文使用的是带 `_edited.pdf` 后缀的最终图。
- `latex/figures/q34_validation_stability.pdf`、`q34_validation_success.pdf`、`q4_outward_adversarial.pdf`：相同文件保留在 `validation/`。
- `inkscape_export/image_generated_references_png/overall_workflow.png` 和 `problem1_circle_counterexample.png`：分别与同目录的 `*_selected.png` 完全相同。

## 当前论文未直接插入的图

以下文件未出现在 LaTeX 的 `\safeimage` 引用中，但有些是制图脚本的输入、生成结果或可编辑源文件，因此暂予保留。

| 类别 | 文件（均位于 `latex/figures/`） |
| --- | --- |
| 早期 SVG 和预览 | `problem1_circle_counterexample_semantic.svg`、`problem2_forward_lateral_region_semantic.svg`、`problem2_reception_condition_semantic.svg`、五张 `*-preview.png`、`problem1_region_nature.png` |
| 问题三分析图 | `q3_belief_contraction.pdf`、`q3_log_spectrum.pdf/.png`、`q3_source_count_performance.pdf`、`q3_method_overview.png` |
| 问题四分析图及拼图素材 | `q4_extreme_boundary_trajectory.pdf/.png`、`q4_method_overview.png`、`q4_testset_coverage_and_extreme.png`、`q4_validation_overview.pdf/.png`、`testset_source_coverage.pdf/.png` |

其中 `q4_extreme_boundary_trajectory.png` 和 `testset_source_coverage.png` 被 `src/make_q4_testset_figure.py` 读取，不能仅凭“未插入正文”删除。

## 保留的重复文件

- `src/generate_paper_figures.py` 与 `inkscape_export/generation_code/generate_paper_figures.py` 内容相同；后者用于使 Inkscape 导出包独立可用。
- `latex/figures/generate_missing_geometry.py` 与 `inkscape_export/generation_code/generate_missing_geometry.py` 内容相同；同样是导出包的独立副本。
- `latex/figures/overall_workflow.png` 与 `inkscape_export/image_generated_references_png/overall_workflow_selected.png` 内容相同；前者是正文正在引用的图，后者是原始参照稿。

`docs/附件1-unpacked/` 与 `docs/附件2-unpacked/` 是 Word 附件展开后的工作目录，不参与论文编译；原始附件保存在 `附件/`。`C023.md` 属于本地过程材料，未纳入本次清理或上传。
