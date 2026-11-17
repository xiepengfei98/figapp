#!/usr/bin/env python3
"""
条码图 (Barcode Plot) — Python 版本
====================================

【图表涵义】
条码图在坐标轴上以垂直（或水平）线条或条块标记数据位置，展示基因组特征
分布、事件发生位置或信号密度。常用于基因组浏览器样式的特征定位展示。

【适用场景】
- 基因组特征（SNP、插入、缺失）的位置展示
- 事件或信号沿一维坐标的分布标记
- 染色体上基因或标记物的位置标注

【数据要求】
- x: 位置坐标，如基因组位置、时间点等（数值）
- y: 可选分类标记，如样本名、染色体号等（分类，可选）
- color: 线条颜色依据列（可选）

=== 列名映射 (columns) =======================================================
  x       — 位置坐标（数值）
  y       — 分组/样本名（可选，用于分条）
  color   — 颜色区分列（可选）
  group   — 分组列（可选）
  facet   — 分面列（可选）

=== @PARAM 说明 ===============================================================
  所有 @PARAM 在右侧面板生成控件，出图后可调参数并重绘。
  select 类型：在标签末尾用 [选项1,选项2] 声明下拉选项。
"""

import sys
import json
from pathlib import Path

import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


# ====================================================================
# 1. 读取配置文件（请勿修改此部分）
# ====================================================================

config_path = sys.argv[1]
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

input_file = Path(config['input'])
output_file = Path(config['output'])
output_pdf = Path(config.get('output_pdf', str(output_file.with_suffix('.pdf'))))
params = config.get('parameters', {})
col_mapping = config.get('columns', {})
colors_data = config.get('colors', {})


# ====================================================================
# 2. 加载全局配置（颜色 + 中文字体，请勿修改此部分）
# ====================================================================

try:
    import figapp_config
    FONT_FAMILY = figapp_config.FONT_FAMILY
    GLOBAL_PALETTE = figapp_config.GLOBAL_PALETTE
except ImportError:
    FONT_FAMILY = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    GLOBAL_PALETTE = ['#E64B35', '#4DBBD5', '#00A087', '#3C5488',
                      '#F39B7F', '#8491B4', '#91D1C2', '#DC0000']

plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False

# 获取颜色列表
active_series = colors_data.get('active_series', '')
if colors_data.get('palette') and len(colors_data['palette']) > 0:
    palette = colors_data['palette']
elif active_series:
    try:
        palette = figapp_config.load_colors(active_series)
    except Exception:
        palette = GLOBAL_PALETTE
else:
    palette = GLOBAL_PALETTE


# ====================================================================
# 3. 读取数据（自动检测编码，请勿修改此部分）
# ====================================================================

def read_data(filepath):
    ext = Path(filepath).suffix.lower()
    if ext in ('.xlsx', '.xls'):
        return pd.read_excel(filepath)
    if ext == '.txt':
        return pd.read_csv(filepath, sep='\t')
    encodings = ['utf-8', 'gbk', 'gb18030', 'latin-1']
    for enc in encodings:
        try:
            return pd.read_csv(filepath, encoding=enc)
        except (UnicodeDecodeError, TypeError):
            continue
    raise ValueError(f"无法识别文件编码: {filepath}")

df = read_data(input_file)


# ====================================================================
# 4. 列名映射 — 按列顺序: 第1列=x, 第2列=y(可选), 第3列=color(可选), 第4列=group(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_color = _df_cols[2] if len(_df_cols) > 2 else None
col_group = _df_cols[3] if len(_df_cols) > 3 else None
col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 4 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 10 | 基础字号
# @PARAM line_width: float = 1.0 | 条码线宽
# @PARAM marker_height: float = 0.8 | 条码高度比例（0~1）

title         = str(params.get('title', ''))
x_label       = str(params.get('x_label', col_x or ''))
y_label       = str(params.get('y_label', col_y or ''))
fig_width     = float(params.get('fig_width', 12))
fig_height    = float(params.get('fig_height', 4))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 10))
line_width    = float(params.get('line_width', 1.0))
marker_height = float(params.get('marker_height', 0.8))

sns.set_style('ticks')
sns.set_context('notebook', font_scale=font_size / 12)

# 重新设置中文字体（seaborn 的 set_style/set_context 会覆盖字体设置）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DengXian', 'DejaVu Sans']
plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False


# ====================================================================
# >>> PLOT CODE >>> — 在此处编写您的绘图代码
#     可用变量: df, col_x, col_y, col_group, col_color, col_facet,
#               col_label, col_size, palette, title, x_label, y_label,
#               fig_width, fig_height, dpi, font_size, alpha
# ====================================================================

# --- 检查必要列 ---
has_x = col_x and col_x in df.columns

if not has_x:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x:
    has_y = col_y and col_y in df.columns
    has_color_col = col_color and col_color in df.columns

    if has_y:
        # 按 y 分条展示
        y_cats = df[col_y].unique()
        y_positions = {cat: i for i, cat in enumerate(y_cats)}
        n_cats = len(y_cats)

        for _, row in df.iterrows():
            y_pos = y_positions[row[col_y]]
            if has_color_col and row[col_color] in df[col_color].values:
                grp_idx = list(df[col_color].unique()).index(row[col_color])
                color = palette[grp_idx % len(palette)]
            else:
                color = palette[0]
            ax.plot(row[col_x], y_pos, marker='|', markersize=10 * marker_height,
                    color=color, lw=0, mew=line_width)

        ax.set_yticks(list(y_positions.values()))
        ax.set_yticklabels(list(y_positions.keys()), fontsize=font_size)
        ax.set_ylim(-0.5, n_cats - 0.5)
        ax.set_ylabel(y_label or col_y, fontsize=font_size)
    else:
        # 简单条码（单行）
        color_col = None
        if col_color and col_color in df.columns:
            color_col = col_color
        elif col_group and col_group in df.columns:
            color_col = col_group

        if color_col:
            for i, (_, row) in enumerate(df.iterrows()):
                grp_idx = 0
                cats = df[color_col].unique()
                val = row[color_col]
                if val in cats:
                    grp_idx = list(cats).index(val)
                color = palette[grp_idx % len(palette)]
                ax.axvline(x=row[col_x], color=color, linewidth=line_width, alpha=0.8)
        else:
            ax.eventplot(df[col_x].dropna(), colors=palette[0],
                         linewidths=line_width, alpha=0.8)
        ax.set_ylim(0, 1)
        ax.set_yticks([])

    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.tick_params(labelsize=font_size - 2)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面提示
    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x)',
            ha='center', va='center', fontsize=14, color='#999',
            transform=ax.transAxes)

# <<< PLOT CODE <<<
# ====================================================================


# ====================================================================
# 6. 保存输出（请勿修改此部分）
# ====================================================================

plt.tight_layout()
fig.savefig(output_file, dpi=dpi, bbox_inches='tight', facecolor='white')
fig.savefig(output_pdf, dpi=dpi, bbox_inches='tight', facecolor='white')
plt.close()

print(f"输出: {output_file.name}")
