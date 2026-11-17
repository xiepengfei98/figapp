#!/usr/bin/env python3
"""
直方图 (Histogram) — Python 版本
=================================

【图表涵义】
直方图展示单变量数据在不同区间内的频率分布，通过柱形高度反映数据集中趋势、
离散程度和分布形态。可叠加密度曲线和均值/中位数参考线。

【适用场景】
- 展示单变量的分布形态和频率特征
- 观察数据的集中趋势、偏态和离群值
- 叠加密度曲线和正态曲线辅助判断分布类型
- 比较多组数据的分布差异（指定 x 分组变量时）

【数据要求】
- y: 数值变量，如基因表达量、测量值等（数值）
- x: 分组变量（可选），指定后按组分别绘制直方图

=== 列名映射 (columns) =======================================================
  y       — 数值变量（Y 轴数值）
  x       — 分组变量（可选，按组着色叠加）
  group   — 二级分组（可选）
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
from scipy import stats


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
# 4. 列名映射 — 按列顺序: 第1列=y(数值变量), 第2列=x(分组变量,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_y = _df_cols[0] if len(_df_cols) > 0 else None
col_x = _df_cols[1] if len(_df_cols) > 1 else None
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
# @PARAM alpha: float = 0.85 | 柱形透明度
# @PARAM num_bins: int = 30 | 分组数（bin）
# @PARAM density_mode: bool = false | 显示密度而非频数
# @PARAM add_density: bool = true | 叠加密度曲线
# @PARAM add_normal: bool = false | 叠加正态分布曲线
# @PARAM add_mean_line: bool = true | 显示均值线
# @PARAM add_median_line: bool = true | 显示中位数线

title         = str(params.get('title', ''))
x_label       = str(params.get('x_label', ''))
y_label       = str(params.get('y_label', ''))
fig_width     = float(params.get('fig_width', 10))
fig_height    = float(params.get('fig_height', 8))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 12))
alpha         = float(params.get('alpha', 0.85))
num_bins      = int(params.get('num_bins', 30))
density_mode  = str(params.get('density_mode', 'false')).lower() == 'true'
add_density   = str(params.get('add_density', 'true')).lower() == 'true'
add_normal    = str(params.get('add_normal', 'false')).lower() == 'true'
add_mean_line = str(params.get('add_mean_line', 'true')).lower() == 'true'
add_median_line = str(params.get('add_median_line', 'true')).lower() == 'true'

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
has_y = col_y and col_y in df.columns

if not has_y:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break

has_x = col_x and col_x in df.columns

fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_y:
    values = df[col_y].dropna().values
    mean_val = np.mean(values)
    median_val = np.median(values)
    std_val = np.std(values, ddof=1)

    if has_x:
        # 分组直方图（多组叠加）
        groups = df[col_x].dropna().unique()
        n_groups = len(groups)
        for i, g in enumerate(groups):
            subset = df.loc[df[col_x] == g, col_y].dropna().values
            ax.hist(subset, bins=num_bins, alpha=alpha,
                    color=palette[i % len(palette)],
                    edgecolor='white', linewidth=0.5,
                    density=density_mode, label=str(g))
        ax.legend(fontsize=font_size - 1)
    else:
        # 单变量直方图
        n, bins, patches = ax.hist(values, bins=num_bins,
            density=density_mode, color=palette[0],
            edgecolor='white', linewidth=0.5, alpha=alpha)

        # 密度曲线
        if add_density and len(values) > 1:
            kde = stats.gaussian_kde(values)
            x_range = np.linspace(values.min(), values.max(), 200)
            kde_y = kde(x_range)
            if not density_mode:
                bin_width = bins[1] - bins[0]
                kde_y = kde_y * len(values) * bin_width
            ax.plot(x_range, kde_y, color=palette[1], linewidth=2.0,
                    linestyle='-', label='Density')

        # 正态曲线
        if add_normal and len(values) > 1 and std_val > 0:
            x_range = np.linspace(values.min(), values.max(), 200)
            norm_y = stats.norm.pdf(x_range, mean_val, std_val)
            if not density_mode:
                bin_width = bins[1] - bins[0]
                norm_y = norm_y * len(values) * bin_width
            ax.plot(x_range, norm_y, color=palette[2], linewidth=1.5,
                    linestyle='--', label=f'Normal(mu={mean_val:.2f}, sd={std_val:.2f})')

        # 均值 / 中位数线
        if add_mean_line:
            ax.axvline(mean_val, color=palette[1], linewidth=1.5,
                       linestyle='--', label=f'Mean = {mean_val:.2f}')
        if add_median_line:
            ax.axvline(median_val, color=palette[3], linewidth=1.5,
                       linestyle=':', label=f'Median = {median_val:.2f}')

    # 标签
    ax.set_xlabel(x_label or col_y, fontsize=font_size)
    ax.set_ylabel(y_label or ('Density' if density_mode else 'Count'), fontsize=font_size)

    # 图例（如有需要）
    if not has_x and (add_density or add_normal or add_mean_line or add_median_line):
        ax.legend(fontsize=font_size - 1, frameon=True, loc='upper right')

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面提示
    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → y 数值列)',
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
