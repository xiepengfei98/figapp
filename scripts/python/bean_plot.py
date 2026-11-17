#!/usr/bin/env python3
"""
豆荚图 (Bean Plot) — Python 版本
=================================

【图表涵义】
豆荚图结合了核密度估计（KDE）分布和散点数据点，以"豆荚"形状展示每组数据的
分布形态，同时显示所有个体数据点，兼具小提琴图和蜂群图的特点。

【适用场景】
- 展示多组数据的分布形态和所有个体观测值
- 替代小提琴图，更强调个体数据点的展示
- 生物医学数据中组间分布对比

【数据要求】
- x: 分组变量，如实验组别（分类）
- y: 数值变量，如表达量、测量值等（数值）

=== 列名映射 (columns) =======================================================
  x       — 分组变量（X 轴分类）
  y       — 数值变量（Y 轴数值）
  group   — 二级分组（可选）
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
import seaborn as sns

from scipy.stats import gaussian_kde


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
# @PARAM alpha: float = 0.7 | 豆荚填充透明度
# @PARAM bean_width: float = 0.4 | 豆荚最大宽度比例
# @PARAM point_size: float = 3 | 数据点大小
# @PARAM point_alpha: float = 0.5 | 数据点透明度

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', col_x or ''))
y_label      = str(params.get('y_label', col_y or ''))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 8))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
alpha        = float(params.get('alpha', 0.7))
bean_width   = float(params.get('bean_width', 0.4))
point_size   = float(params.get('point_size', 3))
point_alpha  = float(params.get('point_alpha', 0.5))

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
    groups = df[col_x].dropna().unique()
    n_groups = len(groups)

    for i, g in enumerate(groups):
        vals = df.loc[df[col_x] == g, col_y].dropna()
        if len(vals) < 2:
            continue
        color = palette[i % len(palette)]

        # KDE 密度估计
        kde = gaussian_kde(vals)
        x_range = np.linspace(vals.min(), vals.max(), 200)
        density = kde(x_range)
        density = density / density.max() * bean_width

        # 绘制豆荚（对称填充）
        ax.fill_betweenx(x_range, i - density, i + density,
                         alpha=alpha, color=color, edgecolor='none')

        # 绘制密度曲线边框
        ax.plot(i + density, x_range, color=color, linewidth=1.0, alpha=0.8)
        ax.plot(i - density, x_range, color=color, linewidth=1.0, alpha=0.8)

        # 绘制个体数据点
        jitter = np.random.uniform(-0.08, 0.08, len(vals))
        ax.scatter(np.full_like(vals, i) + jitter, vals,
                   s=point_size, alpha=point_alpha, color=color, zorder=5)

    # 标签
    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)
    ax.set_xticks(range(n_groups))
    ax.set_xticklabels([str(g) for g in groups], fontsize=font_size - 2)

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
