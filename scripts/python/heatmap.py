#!/usr/bin/env python3
"""
热图 (Heatmap) — Python 版本
=============================

【图表涵义】
热图使用颜色矩阵展示二维数据的数值大小和变化模式，通过颜色渐变直观反映
数据分布，常用于表达谱、相关性矩阵等的可视化。

【适用场景】
- 基因表达谱的热图展示（行=基因，列=样本）
- 相关性矩阵的可视化
- 富集分析结果展示
- 时间序列或条件变化的多维数据展示

【数据要求】
- row: 行标识变量（分类），如基因名，作为行标签
- column: 列标识变量（分类），如样本名，作为列标签
- y: 数值变量（数值），作为热图单元格填充值

=== 列名映射 (columns) =======================================================
  row     — 行标识变量（分类，作为行标签）
  column  — 列标识变量（分类，作为列标签）
  y       — 数值变量（数值，热图填充值）
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
# 4. 列名映射 — 按列顺序: 第1列=x/row(行标识), 第2列=label/column(列标识), 第3列=y(填充值)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None  # 行标识（→col_row）
col_label = _df_cols[1] if len(_df_cols) > 1 else None  # 列标识（→col_column）
col_y = _df_cols[2] if len(_df_cols) > 2 else None  # 填充值
col_row = col_x
col_column = col_label
col_group = col_color = col_facet = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM cmap: str = RdBu_r | 颜色映射 [RdBu_r,coolwarm,viridis,YlOrRd,Blues]
# @PARAM show_values: bool = true | 显示单元格数值
# @PARAM cluster_rows: bool = false | 行聚类
# @PARAM cluster_cols: bool = false | 列聚类

title         = str(params.get('title', ''))
x_label       = str(params.get('x_label', ''))
y_label       = str(params.get('y_label', ''))
fig_width     = float(params.get('fig_width', 10))
fig_height    = float(params.get('fig_height', 8))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 12))
cmap          = str(params.get('cmap', 'RdBu_r'))
show_values   = str(params.get('show_values', 'true')).lower() == 'true'
cluster_rows  = str(params.get('cluster_rows', 'false')).lower() == 'true'
cluster_cols  = str(params.get('cluster_cols', 'false')).lower() == 'true'

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

# --- 检查必要列 ---
has_row = col_row and col_row in df.columns
has_col = col_column and col_column in df.columns
has_val = col_y and col_y in df.columns

if not has_val:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_val = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_row and has_col and has_val:
    # 数据透视：行→行标签，列→列标签，值→填充值
    mat = df.pivot(index=col_row, columns=col_column, values=col_y)

    # 聚类
    if cluster_rows or cluster_cols:
        from scipy.cluster.hierarchy import linkage, leaves_list
        from scipy.spatial.distance import pdist
        if cluster_rows:
            d = pdist(mat.values, metric='euclidean')
            Z = linkage(d, method='average')
            row_idx = leaves_list(Z)
            mat = mat.iloc[row_idx, :]
        if cluster_cols:
            d = pdist(mat.values.T, metric='euclidean')
            Z = linkage(d, method='average')
            col_idx = leaves_list(Z)
            mat = mat.iloc[:, col_idx]

    # 数值标注
    annot = None
    if show_values:
        annot = mat.map(lambda x: f'{x:.2f}' if pd.notna(x) else '')

    # 绘制热图
    sns.heatmap(mat, annot=annot, fmt='', cmap=cmap,
                linecolor='white', linewidths=0.5,
                xticklabels=True, yticklabels=True,
                cbar_kws={'shrink': 0.8},
                annot_kws={'fontsize': font_size - 2},
                ax=ax)

    # 标签
    ax.set_xlabel(x_label or col_column, fontsize=font_size)
    ax.set_ylabel(y_label or col_row, fontsize=font_size)
    ax.tick_params(axis='x', rotation=45, labelsize=font_size - 3)
    ax.tick_params(axis='y', rotation=0, labelsize=font_size - 3)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面提示
    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → row, column, y)',
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
