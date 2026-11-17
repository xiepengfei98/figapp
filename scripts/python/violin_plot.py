#!/usr/bin/env python3
"""
小提琴图 (Violin Plot) — Python 版本
=====================================

【图表涵义】
小提琴图结合箱线图和核密度估计，展示数据分布形态和概率密度。
宽度表示数据在数值区间的密度大小，内部展示关键统计量（中位数、四分位数等），
直观呈现数据的集中趋势、离散程度和分布形状。

【适用场景】
- 比较多组样本的数据分布特征（集中趋势、离散程度、偏态等）
- 展示实验组与对照组之间的表达量差异分布
- 生物医学数据中展示组间分布形态对比
- 替代箱线图，提供更丰富的数据分布信息

【数据要求】
- x: 分组变量，如实验组别、物种名称等（分类）
- y: 数值变量，如基因表达量、测量值等（数值）

=== 列名映射 (columns) =======================================================
  x       — 分组变量（X 轴分类）
  y       — 数值变量（Y 轴数值）
  group   — 二级分组（可选，用于 hue 颜色区分）
  facet   — 分面列（可选，按此列分面子图）

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
# 4. 列名映射 — 按列顺序: 第1列=x(分组变量), 第2列=y(数值变量), 第3列=group(二级分组,可选), 第4列=facet(分面列,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_facet = _df_cols[3] if len(_df_cols) > 3 else None
col_color = col_label = col_size = col_subgroup = None


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
# @PARAM alpha: float = 0.7 | 小提琴透明度
# @PARAM inner: select = box | 内部显示 [box,quartile,point,stick]
# @PARAM show_points: bool = false | 叠加数据点（strip）
# @PARAM show_mean: bool = true | 显示均值标记
# @PARAM horizontal: bool = false | 水平放置
# @PARAM cut: float = 0 | 提琴尾部延伸（0=齐平数据）

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', col_x or ''))
y_label      = str(params.get('y_label', col_y or ''))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 8))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
alpha        = float(params.get('alpha', 0.7))
inner_style  = str(params.get('inner', 'box'))
show_points  = str(params.get('show_points', 'false')).lower() == 'true'
show_mean    = str(params.get('show_mean', 'true')).lower() == 'true'
horizontal   = str(params.get('horizontal', 'false')).lower() == 'true'
cut          = float(params.get('cut', 0))

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
    # 列缺失时自动回退
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
    # 清理缺失值
    plot_df = df[[col_x, col_y]].dropna()
    group_cols = [col_x]
    hue_used = False

    # 判断分组
    if col_group and col_group in df.columns and col_group != col_x:
        group_cols.append(col_group)
        hue_used = True

    # 选择方向
    if horizontal:
        # 水平小提琴
        if hue_used:
            sns.violinplot(data=df, x=col_y, y=col_x, hue=col_group,
                           palette=palette, alpha=alpha, legend=False,
                           inner=inner_style, cut=cut, linewidth=0.8, ax=ax)
        else:
            sns.violinplot(data=df, x=col_y, y=col_x, hue=col_x,
                           palette=palette, alpha=alpha, legend=False,
                           inner=inner_style, cut=cut, linewidth=0.8, ax=ax)
    else:
        # 垂直小提琴（默认）
        if hue_used:
            sns.violinplot(data=df, x=col_x, y=col_y, hue=col_group,
                           palette=palette, alpha=alpha, legend=False,
                           inner=inner_style, cut=cut, linewidth=0.8, ax=ax)
        else:
            sns.violinplot(data=df, x=col_x, y=col_y, hue=col_x,
                           palette=palette, alpha=alpha, legend=False,
                           inner=inner_style, cut=cut, linewidth=0.8, ax=ax)

    # 叠加数据点
    if show_points:
        if horizontal:
            sns.stripplot(data=df, x=col_y, y=col_x, hue=col_x,
                          palette='dark:#333333', alpha=0.35, size=2.5,
                          jitter=0.15, legend=False, ax=ax)
        else:
            sns.stripplot(data=df, x=col_x, y=col_y, hue=col_x,
                          palette='dark:#333333', alpha=0.35, size=2.5,
                          jitter=0.15, legend=False, ax=ax)

    # 均值标记
    if show_mean:
        groups = df[col_x].unique()
        for i, g in enumerate(groups):
            subset = df[df[col_x] == g][col_y].dropna()
            if len(subset) > 0:
                mean_val = subset.mean()
                if horizontal:
                    ax.plot(mean_val, i, marker='D', markersize=7,
                            color='#333333', markeredgecolor='white',
                            markeredgewidth=0.5, zorder=10)
                else:
                    ax.plot(i, mean_val, marker='D', markersize=7,
                            color='#333333', markeredgecolor='white',
                            markeredgewidth=0.5, zorder=10)

    # 标签
    if horizontal:
        ax.set_ylabel(y_label or col_y, fontsize=font_size)
        ax.set_xlabel(x_label or col_x, fontsize=font_size)
    else:
        ax.set_xlabel(x_label or col_x, fontsize=font_size)
        ax.set_ylabel(y_label or col_y, fontsize=font_size)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面
    if col_facet and col_facet in df.columns:
        # 注意：facet 需要使用 FacetGrid，但这里已用 ax，所以只打印提示
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
