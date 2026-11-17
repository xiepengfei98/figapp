#!/usr/bin/env python3
"""
散点图2 (Enhanced Scatter Plot) — Python 版本
===============================================

【图表涵义】
散点图2在标准散点图基础上添加大小映射和边际密度直方图，
气泡大小反映第三维数据，边框直方图展示各分组在 X/Y 轴的分布。

【适用场景】
- 三维数据的可视化（x, y, size）
- 需要同时展示散点和边际分布
- 分组数据的多维展示

【数据要求】
- x: X 轴数值变量（数值）
- y: Y 轴数值变量（数值）
- group: 分组变量（分类）
- size: 气泡大小变量（数值）

=== 列名映射 (columns) =======================================================
  x       — X 轴数值变量（数值）
  y       — Y 轴数值变量（数值）
  group   — 分组变量（分类）
  size    — 气泡大小变量（数值）
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
# 4. 列名映射 — 按列顺序: 第1列=x(X轴数值), 第2列=y(Y轴数值), 第3列=group(分组), 第4列=size(气泡大小,可选)
# ====================================================================
_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_size = _df_cols[3] if len(_df_cols) > 3 else None
col_color = col_facet = col_label = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 9 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 13 | 基础字号
# @PARAM alpha: float = 0.8 | 点透明度
# @PARAM size_scale: float = 8 | 大小缩放因子
# @PARAM show_marginal: bool = true | 显示边际直方图

title         = str(params.get('title', ''))
x_label       = str(params.get('x_label', col_x or ''))
y_label       = str(params.get('y_label', col_y or ''))
fig_width     = float(params.get('fig_width', 9))
fig_height    = float(params.get('fig_height', 7))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 13))
alpha         = float(params.get('alpha', 0.8))
size_scale    = float(params.get('size_scale', 8))
show_marginal = str(params.get('show_marginal', 'true')).lower() == 'true'

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
has_y = col_y and col_y in df.columns
has_group = col_group and col_group in df.columns
has_size_col = col_size and col_size in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    if has_group:
        groups = sorted(df[col_group].unique())
        for i, grp in enumerate(groups):
            subset = df[df[col_group] == grp]
            color = palette[i % len(palette)]
            if has_size_col:
                ax.scatter(subset[col_x], subset[col_y],
                           s=subset[col_size] * size_scale,
                           c=color, alpha=alpha, label=str(grp),
                           edgecolors='white', linewidths=0.5)
            else:
                ax.scatter(subset[col_x], subset[col_y], s=60,
                           c=color, alpha=alpha, label=str(grp),
                           edgecolors='white', linewidths=0.5)

        if show_marginal:
            ax_histx = ax.inset_axes([0, 1.02, 1, 0.15], sharex=ax)
            ax_histy = ax.inset_axes([1.02, 0, 0.15, 1], sharey=ax)
            for i, grp in enumerate(groups):
                subset = df[df[col_group] == grp]
                color = palette[i % len(palette)]
                ax_histx.hist(subset[col_x], bins=10, alpha=0.3, color=color, density=True)
                ax_histy.hist(subset[col_y], bins=10, alpha=0.3, color=color, density=True,
                              orientation='horizontal')
            ax_histx.axis('off')
            ax_histy.axis('off')
    else:
        if has_size_col:
            ax.scatter(df[col_x], df[col_y], s=df[col_size] * size_scale,
                       c=palette[0], alpha=alpha, edgecolors='white', linewidths=0.5)
        else:
            ax.scatter(df[col_x], df[col_y], s=60,
                       c=palette[0], alpha=alpha, edgecolors='white', linewidths=0.5)

    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)
    ax.tick_params(labelsize=font_size - 1)

    if has_group:
        ax.legend(fontsize=font_size - 1, loc='lower right')

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

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
