# 生图参照稿

本目录保存内置生图模型生成的原始 PNG，文件名与论文图位对应，供后续重新设计图像时参考。原始文件仍保存在 Codex 的生成目录；这里是工作区副本。

| 文件 | 对应正文图位 | 当前使用情况 |
| --- | --- | --- |
| `overall_workflow_selected.png` | 四问总流程 | 正文使用同图 `../overall_workflow.png` |
| `overall_workflow_alternative.png` | 四问总流程 | 备选布局，未入正文 |
| `problem1_circle_counterexample_selected.png` | 直径圆反例 | 正文使用同图 `../problem1_circle_counterexample.png` |
| `problem1_wedge_intersection_draft.png` | 测向角域交集 | 仅供版式参考；正文使用精确绘制的 `../problem1_wedge_intersection.pdf` |
| `problem2_forward_lateral_region_draft.png` | 第二检测点双侧候选带 | 仅供版式参考；正文使用 `../problem2_forward_lateral_region.pdf` |
| `problem2_reception_condition_draft.png` | 再次接收的圆盘条件 | 仅供版式参考；正文使用 `../problem2_reception_condition.pdf` |
| `problem3_discovery_coverage_draft.png` | 全向源发现覆盖 | 仅供版式参考；正文使用 `../problem3_discovery_coverage.pdf` |
| `problem4_directional_certificate_draft.png` | 定向源多点证书 | 备选参照；当前问题四正文使用自己的图组 |

带数值坐标的生图原稿存在几何比例或标注偏差，不应直接作为计算证据。正文所用的四张几何 PDF 可用 `../generate_missing_geometry.py` 重建；图位的内容要求仍保留在对应章节的 LaTeX 注释中。
