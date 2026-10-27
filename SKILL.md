---
name: Floorplan-Dimractor
description: >-
  从建筑/门店平面图 PDF 中提取尺寸标注（含设备尺寸、线性标注、橱柜代码），输出带坐标的 JSON。
  原生只支持英制，本封装已改造为支持公制（mm/cm/m），适用于台湾/大陆 1:100 公制施工图。
  典型用途：把平面图 PDF 里的尺寸标注抽出来做面积/工程量估算；阅读设备布置图时快速盘点带尺寸的设备。
  注意：它提取的是「尺寸标注文本」，不是房间多边形；要计算分区净面积，需要图纸本身带房间/墙体尺寸线，
  或结合渲染图人工量取。
---

# Floorplan-Dimractor（公制改造版）

从 PDF 平面图（建筑/门店/设备布置图）抽取**尺寸标注**与**橱柜/设备代码**，输出结构化 JSON（含每个尺寸的像素坐标 bbox），
方便后续做面积/工程量估算或可视化。

## 它能做什么
- 提取 PDF 中的线性尺寸：**英制**（inch、`2' 6"`、分数 inch）与**公制**（`2500MM`、`3.5m`、`350cm`）。
- 公制改造：无单位后缀的数字可按 `--default-unit`（默认 `mm`）处理；`--bare-mm` 把纯数字也当 mm 提取。
- 提取橱柜/设备代码（原版 code_detector 逻辑）。
- 输出 JSON：每个尺寸含 `raw / value_mm / meters / unit / inches / bbox`。
- 可选 `--visualize` 在 PDF 上画 bounding box（需 opencv-python）。

## 不能做什么（重要）
- **不自动算房间/分区面积**：它只抽「标注文本」，不识别房间闭合多边形。
  若图纸有房间尺寸线（如墙长 `3500` 带标注），可抽出数字再人工/脚本配对到房间；
  若图纸是纯设备布置图（如本项目 1-P-08），只有设备尺寸、**没有房间尺寸线**，则抽不出分区净面积——
  这种情况需要另找「带尺寸的建筑平面图」，或把 PDF 渲染成图后用视觉量取分区矩形（近似）。
- 公制 `m / cm` 在标注里必须带单位后缀才被识别；纯数字默认按 mm，可能把页码/年份也当尺寸，
  必要时用 `--bare-mm` 并自行过滤。

## 安装依赖（只需提取时）
```bash
pip install pymupdf pdfplumber regex
# 可选（可视化/视觉）：opencv-python Pillow matplotlib streamlit
```

## 用法
在技能根目录（`Floorplan-Dimractor/`）下运行：
```bash
# 公制提取（推荐台湾 1:100 施工图）：设备尺寸 2500MM 等会被抽出，单位 mm
python main.py "<你的平面图.pdf>" -o out.json -m pymupdf

# 若图纸房间尺寸是纯数字（无 MM 后缀），启用裸数字按 mm：
python main.py "<你的平面图.pdf>" -o out.json --bare-mm

# 英制原样（默认行为也兼容）：
python main.py "<你的平面图.pdf>"
```

## 在本项目（大买家台中大里店）的实际产出
- 输入：`平面图0922_t3-Layout.pdf`（图号 1-P-08，SAMMY DESIGN，比例 1:100）。
- 发现：该图是**设备/家俱布置图**，含 `立风柜 2500MM`、`岛柜 2000MM`、`热风炉 840*935*625` 等设备尺寸与大量分区/公区名称，
  **但无房间边界尺寸线** → 直接算不出分区净面积，需另取带尺寸的建筑平面图，或从渲染图量取。
- 可用的副产品：图内分区标签清单可用于校准「后场/公区占比」假设（见项目交接文件面积更正记录）。

## 脚本位置
- `main.py`：CLI 入口（参数见上）。
- `src/dimension_parser.py`：尺寸解析（英制+公制，`parse_dimension` 返回 mm/meters/unit）。
- `src/pdf_processor.py`：PDF 文本+坐标抽取（pdfplumber / PyMuPDF 两种后端）。
- `src/code_detector.py`：橱柜代码识别。
- `src/visualizer.py`：bbox 可视化。
