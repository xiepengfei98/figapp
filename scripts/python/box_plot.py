#!/usr/bin/env python3
"""
箱线图 (Box Plot) — Python 版本
=================================

【图表涵义】
箱线图展示数据的中位数、四分位数范围、须（whisker）和离群值，直观呈现数据的
集中趋势、离散程度和异常值。箱体表示 IQR，须线延伸至非离群值范围。

【适用场景】
- 比较多组样本的分布特征（中位数、离散度、偏态）
- 识别离群值和异常数据点
- 展示实验组与对照组的表达量差异
- 替代小提琴图，更关注分位数统计信息

【数据要求】
- x: 分组变量，如实验组别、物种名称等（分类）
- y: 数值变量，如基因表达量、测量值等（数值）

=== 列名映射 (columns) =======================================================
  x       — 分组变量（X 轴分类）
  y       — 数值变量（Y 轴数值）
  group   — 二级分组（可选，用于 hue 颜色区分）
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
# 4. 列名映射 — 按列顺序: 第1列=x, 第2列=y
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = col_color = col_facet = col_label = col_size = col_subgroup = None


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
# @PARAM alpha: float = 0.75 | 箱体透明度
# @PARAM notch: bool = false | 显示凹口（中位数置信区间）
# @PARAM horizontal: bool = false | 水平放置
# @PARAM show_points: bool = true | 叠加数据点（strip）
# @PARAM show_mean: bool = true | 显示均值标记
# @PARAM add_violin: bool = false | 箱体背后叠加小提琴图
# @PARAM whis: float = 1.5 | 须线长度（IQR 倍数）

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', col_x or ''))
y_label      = str(params.get('y_label', col_y or ''))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 8))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
alpha        = float(params.get('alpha', 0.75))
notch        = str(params.get('notch', 'false')).lower() == 'true'
horizontal   = str(params.get('horizontal', 'false')).lower() == 'true'
show_points  = str(params.get('show_points', 'true')).lower() == 'true'
show_mean    = str(params.get('show_mean', 'true')).lower() == 'true'
add_violin   = str(params.get('add_violin', 'false')).lower() == 'true'
whis         = float(params.get('whis', 1.5))

sns.set_style('whitegrid')
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

if not has_x or not has_y:
    if not has_x:
        for c in df.columns:
            if not pd.api.types.is_numeric_dtype(df[c]):
                col_x = c
                has_x = True
                break
    if not has_y:
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                col_y = c
                has_y = True
                break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    order = sorted(df[col_x].dropna().unique())

    # 背后叠加小提琴图
    if add_violin:
        if horizontal:
            sns.violinplot(data=df, x=col_y, y=col_x, order=order,
                          inner=None, palette=palette, alpha=0.15, linewidth=0, ax=ax)
        else:
            sns.violinplot(data=df, x=col_x, y=col_y, order=order,
                          inner=None, palette=palette, alpha=0.15, linewidth=0, ax=ax)

    # 箱线图
    flierprops = {
        'markerfacecolor': '#E64B35', 'markeredgecolor': 'black',
        'alpha': 0.7, 'markersize': 4
    }
    if horizontal:
        sns.boxplot(data=df, x=col_y, y=col_x, order=order,
                    width=0.6, notch=notch, linewidth=1.2,
                    fliersize=4, flierprops=flierprops,
                    whis=whis, palette=palette, saturation=1.0, ax=ax)
    else:
        sns.boxplot(data=df, x=col_x, y=col_y, order=order,
                    width=0.6, notch=notch, linewidth=1.2,
                    fliersize=4, flierprops=flierprops,
                    whis=whis, palette=palette, saturation=1.0, ax=ax)

    # 设置箱体透明度
    for i, patch in enumerate(ax.patches):
        if isinstance(patch, matplotlib.patches.PathPatch):
            patch.set_alpha(alpha)

    # 叠加数据点
    if show_points:
        if horizontal:
            sns.stripplot(data=df, x=col_y, y=col_x, order=order,
                         size=4, alpha=0.4, color='black',
                         jitter=0.2, ax=ax, zorder=1)
        else:
            sns.stripplot(data=df, x=col_x, y=col_y, order=order,
                         size=4, alpha=0.4, color='black',
                         jitter=0.2, ax=ax, zorder=1)

    # 均值标记
    if show_mean:
        for i, g in enumerate(order):
            m = df.loc[df[col_x] == g, col_y].mean()
            ax.plot(i, m, marker='D', markersize=8,
                   color='red', markeredgecolor='black',
                   markeredgewidth=0.5, zorder=10)

    # 标签
    if horizontal:
        ax.set_ylabel(y_label or col_x, fontsize=font_size)
        ax.set_xlabel(x_label or col_y, fontsize=font_size)
    else:
        ax.set_xlabel(x_label or col_x, fontsize=font_size)
        ax.set_ylabel(y_label or col_y, fontsize=font_size)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面提示
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
