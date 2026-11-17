#!/usr/bin/env python3
"""
大样本相关性热图 (Large Correlation Heatmap) — Python 版本
============================================================

【图表涵义】
大样本相关性热图自动计算数值列间的相关系数矩阵，并用热图展示，
支持基于层次聚类的行列重排以揭示变量间的聚类模式。

【适用场景】
- 大量变量间的相关性分析
- 基因表达或指标的成对相关
- 需要聚类顺序展示相关矩阵

【数据要求】
数据包含一个样本标识列和多个数值列，自动计算相关系数。
- x: 样本标识列（可选，分类）
- y, group, label, color: 数值列参与相关计算

=== 列名映射 (columns) =======================================================
  x       — 样本标识列（可选，不参与相关计算）
  y       — 数值列1（参与相关计算）
  group   — 数值列2（可选）
  label   — 数值列3（可选）
  color   — 数值列4（可选）
  size    — 数值列5（可选）

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
import seaborn as sns
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform


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
# 4. 列名映射 — 按列顺序: 第1列=x(样本标识), 第2列=facet(分面,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_facet = _df_cols[1] if len(_df_cols) > 1 else None
col_color = col_group = col_label = col_size = col_subgroup = col_y = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 14 | 图片宽度（英寸）
# @PARAM fig_height: float = 12 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM cmap_name: str = RdBu_r | 色图
# @PARAM cluster: bool = true | 是否聚类排序

title       = str(params.get('title', ''))
fig_width   = float(params.get('fig_width', 14))
fig_height  = float(params.get('fig_height', 12))
dpi         = int(params.get('dpi', 300))
font_size   = int(params.get('font_size', 12))
cmap_name   = str(params.get('cmap_name', 'RdBu_r'))
do_cluster  = str(params.get('cluster', 'true')).lower() == 'true'

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

# --- 选择数值列 ---
exclude_cols = {col_x, col_facet} if col_x else set()
if col_facet:
    exclude_cols.add(col_facet)
num_cols = [c for c in df.columns
            if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]

# --- 绘图 ---
if len(num_cols) >= 2:
    cor_df = df[num_cols].corr()

    if do_cluster:
        dist_array = squareform(1 - cor_df.values)
        linkage_matrix = linkage(dist_array, method='average')
        order = leaves_list(linkage_matrix)
        cor_ordered = cor_df.iloc[order, order]
    else:
        cor_ordered = cor_df

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    sns.heatmap(cor_ordered, cmap=cmap_name, center=0, vmin=-1, vmax=1,
                square=True, linewidths=0.1, linecolor='#ffffff',
                cbar_kws={'label': 'Correlation', 'shrink': 0.7},
                xticklabels=cor_ordered.columns,
                yticklabels=cor_ordered.index, ax=ax)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

    ax.tick_params(axis='both', labelsize=font_size - 4)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=90, ha='right', fontsize=font_size - 4)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=font_size - 4)

    cbar = ax.collections[0].colorbar
    if cbar:
        cbar.ax.tick_params(labelsize=font_size - 1)

else:
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.text(0.5, 0.5, '需要至少 2 个数值列计算相关系数',
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
