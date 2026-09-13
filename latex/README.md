# B 题 LaTeX 论文模板

本目录是“无线电干扰源的快速自动定位与清除”专用论文骨架。唯一编译入口为 `main.tex`；每个论文大标题在 `chapters/` 下拥有一个独立文件夹，文件夹内只保留一个 `main.tex`。

## 快速编译

在本目录打开 PowerShell，运行（无需安装 Perl）：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

该命令生成电子版：第一页为摘要页，不包含承诺书和编号专用页。若需按纸质版装订格式生成带官方前置页的版本，运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build-paper.ps1
```

纸质版的前两页由 `figures/format2026_promise.pdf` 和 `figures/format2026_number.pdf` 导入官方 Word 格式文件；摘要页从正文页码 1 开始编号。

也可以手动依次运行：

```powershell
xelatex -interaction=nonstopmode -halt-on-error main.tex
biber main
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

若另外安装了 Perl，也可使用 `latexmk`：

```powershell
latexmk -xelatex -interaction=nonstopmode main.tex
```

模板使用 `ctexart`，必须用 XeLaTeX 或 LuaLaTeX，不能用 pdfLaTeX。首次编译时 MiKTeX 可能提示安装缺失宏包，请允许安装。

若系统没有 Biber，可先安装 Biber；应急情况下，可注释 `config/packages.tex` 中的 `biblatex` 和 `addbibresource` 两行，再把 `chapters/参考文献/main.tex` 改为标准 `thebibliography` 环境。正式交稿前建议恢复 Biber，以获得稳定的中文文献处理。

## 目录职责

- `config/`：宏包、页面格式和公共命令。官方格式变化时优先修改这里。
- `chapters/`：论文正文；每个一级大标题一个文件夹。
- `chapters/问题一/main.tex` 至 `chapters/问题四/main.tex`：各问的分析、模型或策略、算法和结果集中写在同一个文件中。
- `figures/`：论文图片。模板中的图片不存在时会显示可编译的占位框。
- `code/`：附录引用的源程序。
- `references/`：BibLaTeX 文献数据库。
- `tests/`：模板结构与必备内容检查。

## 推荐填写顺序

1. 在四个问题目录中完善模型、算法和实验结果。
2. 将图片放入 `figures/`，文件名与 `\safeimage` 的路径一致。
3. 填写问题三、问题四的正式测试结果表，并保留模拟器日志原文件名。
4. 根据全文结果回写问题分析、摘要、模型评价和参考文献。
5. 搜索 `\placeholder` 或“待填写”，清理所有占位内容。
6. 按当年官方论文格式规范核对封面、字号、页边距、页码和提交材料。

正式电子版按规范不设置目录；如有其他用途需要目录，应另行制作副本，不要把目录加入竞赛电子版。

## 自动检查

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File latex/tests/check_structure.ps1
```

检查通过只表示工程结构和赛题必备栏目齐全；最终数值、图表、引用和论证仍需人工复核。
