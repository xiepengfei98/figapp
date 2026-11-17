#!/usr/bin/env python3
"""
密度图 (Density Plot) — Python 版本
====================================

【图表涵义】
密度图通过核密度估计展示多组数据的分布曲线，直观反映数据的集中趋势、
离散程度和偏态特征。曲线下方的面积表示概率密度。

【适用场景】
- 比较多组样本的分布形态（位置、展布、偏态）
- 展示实验组与对照组的表达量分布差异
- 作为直方图的平滑替代方案
- 叠加多条曲线对比不同条件的分布变化

【数据要求】
- x: 分组变量，如实验组别、物种名称等（分类）
- y: 数值变量，如基因表达量、测量值等（数值）

=== 列名映射 (columns) =======================================================
  x       — 分组变量（X 轴分类）
  y       — 数值变量（Y 轴数值）
  group   — 二级分组（可选，用于 hue 颜色区分）
  facet   — 分面列（可选，按此列分面子图）
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
# 4. 列名映射 — 按列顺序: 第1列=x(分组), 第2列=y(数值), 第3列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_facet = _df_cols[2] if len(_df_cols) > 2 else None
col_group = col_color = col_label = col_size = col_subgroup = None


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
# @PARAM alpha: float = 0.25 | 密度填充透明度
# @PARAM line_width: float = 2.0 | 密度线宽
# @PARAM bw_adjust: float = 1.0 | 带宽调节因子（>1 更平滑，<1 更尖锐）
# @PARAM fill_density: bool = true | 填充曲线下面积
# @PARAM cumulative: bool = false | 累计密度
# @PARAM add_rug: bool = false | 添加地毯图（数据点标记）
# @PARAM add_histogram: bool = false | 叠加直方图

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', col_x or ''))
y_label      = str(params.get('y_label', col_y or ''))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 8))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
alpha        = float(params.get('alpha', 0.25))
line_width   = float(params.get('line_width', 2.0))
bw_adjust    = float(params.get('bw_adjust', 1.0))
fill_density = str(params.get('fill_density', 'true')).lower() == 'true'
cumulative   = str(params.get('cumulative', 'false')).lower() == 'true'
add_rug      = str(params.get('add_rug', 'false')).lower() == 'true'
add_histogram = str(params.get('add_histogram', 'false')).lower() == 'true'

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
    # 确定分组
    groups = df[col_x].dropna().unique()
    group_order = sorted(groups)

    # 叠加直方图
    if add_histogram:
        for i, g in enumerate(group_order):
            subset = df.loc[df[col_x] == g, col_y].dropna()
            ax.hist(subset, bins=30, alpha=0.3,
                    color=palette[i % len(palette)],
                    density=True, label=f'{g}' if alpha > 0.5 else None)

    # 核密度曲线
    for i, g in enumerate(group_order):
        subset = df.loc[df[col_x] == g, col_y].dropna()
        color = palette[i % len(palette)]
        sns.kdeplot(
            data=subset,
            fill=fill_density,
            alpha=alpha,
            color=color,
            linewidth=line_width,
            bw_adjust=bw_adjust,
            cumulative=cumulative,
            label=str(g),
            ax=ax
        )

    # 地毯图
    if add_rug:
        for i, g in enumerate(group_order):
            subset = df.loc[df[col_x] == g, col_y].dropna()
            sns.rugplot(data=subset, height=0.03, alpha=0.5,
                        lw=0.8, color=palette[i % len(palette)], ax=ax)

    # 标签
    ax.set_xlabel(x_label or col_y, fontsize=font_size)
    ax.set_ylabel(y_label or 'Density', fontsize=font_size)

    # 图例
    if len(group_order) > 0:
        ax.legend(fontsize=font_size - 1)

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
