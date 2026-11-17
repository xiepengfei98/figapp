#!/usr/bin/env python3
"""
热图决策树 (Heatmap with Dendrogram) — Python 版本
====================================================

【图表涵义】
热图决策树结合热图和层次聚类树状图，同时展示数据的表达模式和聚类关系，
行和列均根据聚类结果重新排序。

【适用场景】
- 基因表达谱的聚类热图展示
- 样本和基因的双向聚类分析
- 展示表达数据的全局模式和聚类结构

【数据要求】
数据为宽格式，一列为行标识（如基因名），其余列为数值矩阵。
- x: 行标识列（如基因名，分类）
- 其余列自动作为数值矩阵

=== 列名映射 (columns) =======================================================
  x       — 行标识列（分类，作为行标签）
  其余非 x 非 facet 的列作为数值矩阵
  facet   — 分面列（可选，不参与聚类）

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
from scipy.cluster.hierarchy import dendrogram, linkage


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
# 4. 列名映射 — 按列顺序: 第1列=x(行标识), 其余数值列自动为矩阵
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = col_group = col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 10 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM cmap_name: str = RdBu_r | 色图
# @PARAM cluster_method: str = complete | 聚类方法
# @PARAM show_annot: bool = false | 显示数值标签

title          = str(params.get('title', ''))
fig_width      = float(params.get('fig_width', 12))
fig_height     = float(params.get('fig_height', 10))
dpi            = int(params.get('dpi', 300))
font_size      = int(params.get('font_size', 12))
cmap_name      = str(params.get('cmap_name', 'RdBu_r'))
cluster_method = str(params.get('cluster_method', 'complete'))
show_annot     = str(params.get('show_annot', 'false')).lower() == 'true'

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

# --- 判断是否有行标识列和数据列 ---
has_index = col_x and col_x in df.columns
exclude = {col_x, col_facet} if col_x else set()
if col_facet:
    exclude.add(col_facet)
value_cols = [c for c in df.columns
              if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]

# --- 绘图 ---
if has_index and len(value_cols) >= 2:
    plot_df = df.set_index(col_x)
    plot_df = plot_df[value_cols].select_dtypes(include=[np.number])

    g = sns.clustermap(plot_df, method=cluster_method, metric='euclidean',
                       cmap=cmap_name, center=plot_df.values.flatten().mean(),
                       linewidths=1, linecolor='white',
                       figsize=(fig_width, fig_height),
                       cbar_kws={'label': 'Expression', 'shrink': 0.7},
                       dendrogram_ratio=0.12,
                       xticklabels=True, yticklabels=True,
                       annot=show_annot, fmt='.2f' if show_annot else None)

    g.ax_heatmap.set_xlabel('')
    g.ax_heatmap.set_ylabel('')
    g.ax_heatmap.tick_params(axis='both', labelsize=font_size - 1)
    g.ax_heatmap.set_xticklabels(g.ax_heatmap.get_xticklabels(),
                                 rotation=45, ha='right', fontsize=font_size - 1)
    g.ax_heatmap.set_yticklabels(g.ax_heatmap.get_yticklabels(),
                                 rotation=0, fontsize=font_size - 1)

    if title:
        g.fig.suptitle(title, fontsize=font_size + 2, fontweight='bold', y=1.02)

    # 用 clustermap 的 figure 覆盖 fig 变量，让 Section 6 保存
    fig = g.fig

else:
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x 为行标识，其余数值列自动为矩阵)',
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
