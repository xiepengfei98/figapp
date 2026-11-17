#!/usr/bin/env python3
"""
马赛克比例图 (Mosaic Proportion Plot) — Python 版本
=====================================================

【图表涵义】
马赛克比例图用面积成比例的矩形展示两个分类变量的交叉频数，
矩形宽度反映列比例，高度反映行比例。

【适用场景】
- 展示两个分类变量的交叉频数比例
- 列联表的可视化
- 替代堆叠条形图的比例展示

【数据要求】
- x: 行变量（分类）
- y: 列变量（分类）
- size: 计数（数值）

=== 列名映射 (columns) =======================================================
  x       — 行变量（分类）
  y       — 列变量（分类）
  size    — 计数（数值）
  facet   — 分面列（可选）
"""

import sys
import json
from pathlib import Path

import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
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
# 4. 列名映射 — 按列顺序: 第1列=x(行变量), 第2列=y(列变量), 第3列=size(计数), 第4列=facet(分面,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_size = _df_cols[2] if len(_df_cols) > 2 else None
col_facet = _df_cols[3] if len(_df_cols) > 3 else None
col_color = col_group = col_label = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Mosaic Proportion | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.85 | 矩形透明度

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 7))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
alpha      = float(params.get('alpha', 0.85))

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
has_row = col_x and col_x in df.columns
has_col = col_y and col_y in df.columns
has_cnt = col_size and col_size in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_row and has_col and has_cnt:
    row_levels = df[col_x].unique()
    col_levels = df[col_y].unique()
    n_cols = len(col_levels)

    # 计算行比例
    row_totals = df.groupby(col_x)[col_size].sum()
    row_heights = row_totals / row_totals.sum()

    y_bottom = 0
    for r in row_levels:
        row_h = row_heights[r]
        col_total = row_totals[r]
        x_left = 0

        for c in col_levels:
            mask = (df[col_x] == r) & (df[col_y] == c)
            cnt = df.loc[mask, col_size].sum()
            if cnt > 0:
                w = cnt / col_total
                ci = list(col_levels).index(c) % len(palette)
                ax.add_patch(plt.Rectangle(
                    (x_left, y_bottom), w, row_h,
                    facecolor=palette[ci], edgecolor='white',
                    linewidth=1.5, alpha=alpha))
                if w > 0.08:
                    ax.text(x_left + w / 2, y_bottom + row_h / 2,
                            f'{w * 100:.0f}%', ha='center', va='center',
                            fontsize=font_size - 3, color='white', fontweight='bold')
                x_left += w
        y_bottom += row_h

    # 行标签
    y_centers = (np.cumsum([0] + list(row_heights.values[:-1])) +
                 np.array(list(row_heights.values)) / 2)
    for i, r in enumerate(row_levels):
        ax.text(-0.02, y_centers[i], str(r), ha='right', va='center',
                fontsize=font_size, fontweight='bold')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

    # 图例
    handles = [Patch(facecolor=palette[i % n_cols], label=str(c))
               for i, c in enumerate(col_levels)]
    ax.legend(handles=handles, title=col_y, loc='upper right',
              fontsize=font_size - 1)

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x=row, y=col, size=count)',
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
