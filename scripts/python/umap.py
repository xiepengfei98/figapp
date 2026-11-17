#!/usr/bin/env python3
"""
UMAP 图 (UMAP Dimensionality Reduction Plot) — Python 版本
============================================================

【图表涵义】
UMAP 图展示高维数据降维后的聚类结构，UMAP 是非线性降维方法，
能保留数据的局部和全局结构。

【适用场景】
- 高维数据的聚类和群体结构探索
- 单细胞 RNA-seq 数据的可视化
- 与 PCA 互补的非线性降维展示

【数据要求】
- x: UMAP1 坐标值（数值）
- y: UMAP2 坐标值（数值）
- group: 聚类/分组变量（可选）

=== 列名映射 (columns) =======================================================
  x       — UMAP1 坐标值（数值）
  y       — UMAP2 坐标值（数值）
  group   — 聚类/分组变量（可选）
  label   — 样本标签（可选）
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
from matplotlib.patches import Ellipse
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
# 4. 列名映射 — 按列顺序: 第1列=x(UMAP1), 第2列=y(UMAP2), 第3列=group(分组,可选), 第4列=label(样本标签,可选), 第5列=facet(分面列,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_label = _df_cols[3] if len(_df_cols) > 3 else None
col_facet = _df_cols[4] if len(_df_cols) > 4 else None
col_color = col_size = col_subgroup = None


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
# @PARAM alpha: float = 0.85 | 点透明度
# @PARAM add_ellipse: bool = true | 添加置信椭圆
# @PARAM add_labels: bool = false | 显示样本标签
# @PARAM ellipse_level: float = 0.95 | 椭圆置信水平

title         = str(params.get('title', ''))
x_label       = str(params.get('x_label', col_x or ''))
y_label       = str(params.get('y_label', col_y or ''))
fig_width     = float(params.get('fig_width', 10))
fig_height    = float(params.get('fig_height', 8))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 12))
alpha         = float(params.get('alpha', 0.85))
add_ellipse   = str(params.get('add_ellipse', 'true')).lower() == 'true'
add_labels    = str(params.get('add_labels', 'false')).lower() == 'true'
ellipse_level = float(params.get('ellipse_level', 0.95))

sns.set_style('ticks')
sns.set_context('notebook', font_scale=font_size / 12)

# 重新设置中文字体（seaborn 的 set_style/set_context 会覆盖字体设置）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DengXian', 'DejaVu Sans']
plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False

# ====================================================================
# 置信椭圆辅助函数
# ====================================================================

def add_ellipse_patch(ax, x, y, color, level=0.95, alpha_fill=0.12):
    if len(x) < 3 or len(y) < 3:
        return
    cov = np.cov(x, y)
    if cov.shape != (2, 2) or np.isnan(cov).any():
        return
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]
    angle = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
    n_std = np.sqrt(-2 * np.log(1 - level))
    width, height = 2 * n_std * np.sqrt(vals)
    e = Ellipse(xy=(np.mean(x), np.mean(y)),
                width=width, height=height, angle=angle,
                edgecolor=color, facecolor=color, alpha=alpha_fill)
    ax.add_patch(e)


# ====================================================================
# >>> PLOT CODE >>> — 在此处编写您的绘图代码
#     可用变量: df, col_x, col_y, col_group, col_color, col_facet,
#               col_label, col_size, palette, title, x_label, y_label,
#               fig_width, fig_height, dpi, font_size, alpha
# ====================================================================

# --- 检查必要列 ---
has_x = col_x and col_x in df.columns
has_y = col_y and col_y in df.columns

if not has_x or not has_y:
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not has_x and len(num_cols) >= 1:
        col_x = num_cols[0]
        has_x = True
    if not has_y and len(num_cols) >= 2:
        col_y = num_cols[1]
        has_y = True

has_group = col_group and col_group in df.columns
has_label_col = col_label and col_label in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    if has_group:
        for i, (g, grp) in enumerate(df.groupby(col_group)):
            color = palette[i % len(palette)]
            ax.scatter(grp[col_x], grp[col_y], s=80, alpha=alpha,
                       color=color, label=str(g),
                       edgecolors='white', linewidths=0.3)
            if add_ellipse and len(grp) >= 3:
                add_ellipse_patch(ax, grp[col_x].values, grp[col_y].values,
                                  color, level=ellipse_level)
        ax.legend(fontsize=font_size - 1)
    else:
        ax.scatter(df[col_x], df[col_y], s=80, alpha=alpha,
                   color=palette[0], edgecolors='white', linewidths=0.3)

    if add_labels and has_label_col:
        for _, row in df.iterrows():
            ax.text(row[col_x], row[col_y], str(row[col_label]),
                    fontsize=font_size - 3, ha='center', va='bottom')

    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x, y)',
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
