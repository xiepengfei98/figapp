#!/usr/bin/env python3
"""
复杂热图 (Complex Heatmap) — Python 版本
========================================

【图表涵义】
复杂热图在标准热图基础上添加行列注释条，展示多维数据的表达模式、
分组信息和聚类关系，是生物信息学中最常用的可视化方式之一。

【适用场景】
- 基因表达谱的全面展示（表达式值 + 基因分组 + 通路注释）
- 多维数据的聚类和模式识别
- 需要展示样本分组和基因注释的热图

【数据要求】
数据应为宽格式（wide format），每行为一个基因/特征：
- x: 行标识列（如基因名），作为行标签
- 其余数值列自动作为热图值矩阵
- 非数值列自动作为行注释

=== 列名映射 (columns) =======================================================
  x       — 行标识列（如基因名），作为行标签
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
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
import seaborn as sns
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import pdist


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
# 4. 列名映射 — 按列顺序: 第1列=x(行标识列), 第2列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_facet = _df_cols[1] if len(_df_cols) > 1 else None
col_y = col_group = col_color = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 9 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM cmap: str = RdBu_r | 颜色映射 [RdBu_r,coolwarm,viridis,YlOrRd,Blues]
# @PARAM vmin: float = -3 | 颜色最小值
# @PARAM vmax: float = 3 | 颜色最大值
# @PARAM cluster_rows: bool = true | 行聚类
# @PARAM cluster_cols: bool = true | 列聚类

title         = str(params.get('title', ''))
fig_width     = float(params.get('fig_width', 12))
fig_height    = float(params.get('fig_height', 9))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 12))
cmap          = str(params.get('cmap', 'RdBu_r'))
vmin          = float(params.get('vmin', -3))
vmax          = float(params.get('vmax', 3))
cluster_rows  = str(params.get('cluster_rows', 'true')).lower() == 'true'
cluster_cols  = str(params.get('cluster_cols', 'true')).lower() == 'true'

sns.set_style('white')
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

# --- 自动检测宽格式数据 ---
if col_x and col_x in df.columns:
    row_name_col = col_x
else:
    # 第一列作为行名
    row_name_col = df.columns[0]

# 分离数值列和非数值列
numeric_cols = []
annotation_cols = {}
value_col_names = []

for c in df.columns:
    if c == row_name_col:
        continue
    if pd.api.types.is_numeric_dtype(df[c]):
        numeric_cols.append(c)
        value_col_names.append(c)
    else:
        annotation_cols[c] = df[c].fillna('NA').astype(str).values

# 提取矩阵
row_names = df[row_name_col].values
mat = df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0).values.astype(np.float64)
n_rows, n_cols = mat.shape

if n_rows == 0 or n_cols == 0:
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.text(0.5, 0.5, '请上传宽格式数据\n(行=基因/特征，列=样本/条件)',
            ha='center', va='center', fontsize=14, color='#999',
            transform=ax.transAxes)
else:
    # 聚类
    row_order = np.arange(n_rows)
    col_order = np.arange(n_cols)
    if cluster_rows and n_rows > 2:
        d = pdist(mat, metric='euclidean')
        Z = linkage(d, method='average')
        row_order = leaves_list(Z)
    if cluster_cols and n_cols > 2:
        d = pdist(mat.T, metric='euclidean')
        Z = linkage(d, method='average')
        col_order = leaves_list(Z)

    mat = mat[row_order][:, col_order]
    row_names = row_names[row_order]
    col_names = [value_col_names[i] for i in col_order]

    # 行注释排序
    ann_data = {}
    for ann_name in annotation_cols:
        ann_data[ann_name] = annotation_cols[ann_name][row_order]

    # --- 布局 ---
    n_ann = len(ann_data)
    w_heat = 0.7
    w_ann = 0.03 * max(n_ann, 1)
    w_cbar = 0.03
    w_gap = 0.01

    fig = plt.figure(figsize=(fig_width, fig_height))

    # 列注释高度
    has_col_ann = False

    gs = GridSpec(2, 4, figure=fig,
                  width_ratios=[w_ann, w_heat, w_gap * 5, w_cbar],
                  height_ratios=[0.03 if has_col_ann else 0.01, 0.99],
                  hspace=0.02, wspace=0.01)

    ax_heat = fig.add_subplot(gs[1, 1])

    # --- 绘制热图 ---
    im = ax_heat.imshow(mat, aspect='auto', cmap=cmap, vmin=vmin, vmax=vmax)

    # 列名
    ax_heat.set_xticks(np.arange(n_cols))
    ax_heat.set_xticklabels(col_names, rotation=45, ha='right',
                            fontsize=font_size - 3)
    # 行名
    ax_heat.set_yticks(np.arange(n_rows))
    ax_heat.set_yticklabels(row_names, fontsize=font_size - 3)

    # 网格线
    for i in range(n_rows + 1):
        ax_heat.axhline(i - 0.5, color='white', linewidth=0.3)
    for j in range(n_cols + 1):
        ax_heat.axvline(j - 0.5, color='white', linewidth=0.3)

    # --- 行注释 ---
    ax_row_ann = fig.add_subplot(gs[1, 0])
    for k_idx, (ann_name, ann_vals) in enumerate(ann_data.items()):
        unique_vals = sorted(set(ann_vals))
        cat_palette = {v: palette[i % len(palette)] for i, v in enumerate(unique_vals)}
        for yi in range(len(ann_vals)):
            ax_row_ann.add_patch(plt.Rectangle(
                (k_idx - 0.4, yi - 0.5), 0.8, 1,
                facecolor=cat_palette.get(ann_vals[yi], 'grey'),
                edgecolor='white', linewidth=0.2))
        ax_row_ann.text(k_idx, n_rows + 0.5, ann_name,
                       ha='center', va='bottom',
                       fontsize=font_size - 3, rotation=90)

    ax_row_ann.set_xlim(-0.5, max(n_ann, 1) - 0.5)
    ax_row_ann.set_ylim(n_rows - 0.5, -0.5)
    ax_row_ann.set_xticks([])
    ax_row_ann.set_yticks([])
    ax_row_ann.set_frame_on(False)

    # --- 色标 ---
    ax_cbar = fig.add_subplot(gs[1, 3])
    cbar = plt.colorbar(im, cax=ax_cbar, orientation='vertical')
    cbar.ax.tick_params(labelsize=font_size - 3)

    # --- 标题 ---
    if title:
        fig.suptitle(title, fontsize=font_size + 2, fontweight='bold', y=0.98)

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
