# Inkscape 导出包

这个目录整理了前两问附近使用的参照图、正文图和生成代码。

## image_generated_references_png

这些是内置生图模型生成或选用的 PNG 参照图。Inkscape 可以打开，但它们是位图，适合查看、描摹、排版，不适合直接编辑单个线条和文字。

## inkscape_openable_figures

这些是正文使用或可复现生成的 PDF/SVG 图。Inkscape 可以直接打开；PDF 导入时选择文本/字体处理方式后可继续编辑。

## generation_code

这些是生成上述可复现图的 Python 脚本，以及参照图说明 README。

注意：当前命令行环境没有找到 `inkscape` 可执行文件，所以这里没有调用 Inkscape 批量转换；导出的 PDF/SVG/PNG 格式本身均为 Inkscape 支持格式。
