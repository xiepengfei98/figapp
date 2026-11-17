#!/usr/bin/env python3
"""
Hi-C 热图 (Hi-C Contact Matrix Heatmap) — Python 版本
======================================================

【图表涵义】
Hi-C 热图展示基因组区域间的接触频率矩阵，颜色从浅到深反映
接触强度，揭示染色体的空间结构和相互作用。

【适用场景】
- 展示 Hi-C 染色质交互数据
- 展示基因组区域间的接触频率
- 展示任何对称的交互/连接矩阵

【数据要求】
数据为矩阵格式，包含区域标识列和多个数值列作为矩阵。
- x: 区域标识列（分类，行标签）
- y, group, label, color, size: 数值列作为矩阵列

=== 列名映射 (columns) =======================================================
  x       — 区域标识列（分类，行标签）
  其余数值列自动作为矩阵的列

=== @PARAM 说明 ===============================================================
  所有 @PARAM 在右侧面板生成控件，出图后可调参数并重绘。
"""

import sys
import json
from pathlib import Path

import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
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
# 4. 列名映射 — 按列顺序: 第1列=x(区域标识), 其余数值列自动为矩阵
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = col_group = col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM cmap_name: str =  | 色图（空则使用默认渐变色）

title      = str(params.get('title', ''))
x_label    = str(params.get('x_label', ''))
y_label    = str(params.get('y_label', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 6))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
cmap_name  = str(params.get('cmap_name', ''))

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

# --- 选择矩阵列 ---
has_index = col_x and col_x in df.columns
exclude = {col_x, col_facet} if col_x else set()
if col_facet:
    exclude.add(col_facet)
num_cols = [c for c in df.columns
            if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_index and len(num_cols) >= 2:
    mat = df[num_cols].values

    if cmap_name and cmap_name in plt.colormaps():
        cmap = plt.get_cmap(cmap_name)
    else:
        cmap = LinearSegmentedColormap.from_list(
            'hic_cmap',
            [palette[-3] if len(palette) > 2 else '#FFFFCC',
             palette[1] if len(palette) > 1 else '#FDAE61',
             palette[0]],
            N=256)

    im = ax.imshow(mat, cmap=cmap, aspect='equal', vmin=0, vmax=mat.max())

    row_labels = df[col_x].tolist()
    col_labels = [f'P{i+1}' for i in range(len(num_cols))]

    ax.set_xticks(range(len(num_cols)))
    ax.set_yticks(range(len(row_labels)))
    ax.set_xticklabels(col_labels, fontsize=font_size - 2, rotation=45, ha='right')
    ax.set_yticklabels(row_labels, fontsize=font_size - 2)
    ax.set_xlabel(x_label or 'Genomic Region', fontsize=font_size)
    ax.set_ylabel(y_label or col_x, fontsize=font_size)
    ax.tick_params(labelsize=font_size - 1)

    cbar = plt.colorbar(im, ax=ax, shrink=0.82)
    cbar.set_label('Contact Frequency', fontsize=font_size)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x 为行标签，其余列自动为矩阵)',
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
