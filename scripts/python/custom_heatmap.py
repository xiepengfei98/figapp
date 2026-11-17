#!/usr/bin/env python3
"""
自定义热图 (Custom Heatmap) — Python 版本
===========================================

【图表涵义】
自定义热图用色块矩阵展示基因表达或其他数值数据，每个单元格标注数值，
支持自定义发散色图。

【适用场景】
- 展示基因表达矩阵
- 展示小型数据表的数值模式
- 需要每个格子标注精确数值的场景

【数据要求】
宽格式数据，第一列为行标识（如基因名），其余列为数值矩阵。
- x: 行标识列（分类，如基因名）
- 其余数值列自动作为矩阵列

=== 列名映射 (columns) =======================================================
  x       — 行标识列（分类）
  其余非 x 列作为数值矩阵
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
# 4. 列名映射 — 按列顺序: 第1列=x(行标识), 其余为数值矩阵列
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_facet = col_y = col_group = col_color = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM cmap_name: str =  | 色图（空则用默认发散色图）

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 8))
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

# --- 检查数据 ---
has_index = col_x and col_x in df.columns

exclude_cols = {col_x}
if col_facet:
    exclude_cols.add(col_facet)

val_cols = [c for c in df.columns
            if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_index and len(val_cols) > 0:
    row_labels = df[col_x].tolist()
    n_rows = len(row_labels)
    n_cols = len(val_cols)
    mat = df[val_cols].values
    vmin, vmax = mat.min(), mat.max()
    vcenter = np.median(mat)

    if cmap_name and cmap_name in plt.colormaps():
        cmap = plt.get_cmap(cmap_name)
    else:
        cmap = LinearSegmentedColormap.from_list(
            'custom_div',
            [palette[3] if len(palette) > 3 else '#313695',
             '#f7f7f7',
             palette[0]],
            N=256)

    im = ax.imshow(mat, cmap=cmap, aspect='auto')

    # 数值标注
    for i in range(n_rows):
        for j in range(n_cols):
            val = mat[i, j]
            threshold = (vmax - vmin) * 0.3
            text_color = '#ffffff' if abs(val - vcenter) > threshold else '#222222'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=font_size - 3, color=text_color)

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(val_cols, rotation=45, ha='right', fontsize=font_size - 1)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(row_labels, fontsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=15)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, label='Value')
    cbar.ax.tick_params(labelsize=font_size - 1)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x 为行标识，其余列为数值矩阵)',
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
