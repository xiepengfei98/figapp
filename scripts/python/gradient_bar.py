#!/usr/bin/env python3
"""
渐变柱状图 (Gradient Bar Chart) — Python 版本
===============================================

【图表涵义】
渐变柱状图使用颜色渐变反映额外数值维度，每个柱体的颜色根据
某个评分/指标值从低到高渐变，同时展示数值大小和评分高低。

【适用场景】
- 展示分类数据的同时反映另一个维度的指标
- 用颜色渐变强调高低差异的数据展示
- 结合条形高度和颜色传达二维信息

【数据要求】
- x: 类别变量（柱体标签）
- y: 数值变量（柱体高度）
- color: 渐变评分变量（数值，决定柱体颜色）

=== 列名映射 (columns) =======================================================
  x       — 类别变量（柱体标签，分类）
  y       — 数值变量（柱体高度，数值）
  color   — 渐变评分（数值，决定柱体颜色）
  facet   — 分面列（可选）

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
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, LinearSegmentedColormap
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
# 4. 列名映射 — 按列顺序: 第1列=x(类别), 第2列=y(数值), 第3列=color(渐变评分)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_color = _df_cols[2] if len(_df_cols) > 2 else None
col_group = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 1.0 | 柱体透明度
# @PARAM cmap_name: str =  | 渐变色图名（空则用 palette 首尾色）
# @PARAM colorbar_label: str = Score | 色标标签

title           = str(params.get('title', ''))
x_label         = str(params.get('x_label', col_x or ''))
y_label         = str(params.get('y_label', col_y or ''))
fig_width       = float(params.get('fig_width', 10))
fig_height      = float(params.get('fig_height', 7))
dpi             = int(params.get('dpi', 300))
font_size       = int(params.get('font_size', 12))
alpha           = float(params.get('alpha', 1.0))
cmap_name       = str(params.get('cmap_name', ''))
colorbar_label  = str(params.get('colorbar_label', 'Score'))

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
has_score = col_color and col_color in df.columns

if not has_x:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break
if not has_y:
    for c in df.columns:
        if c != col_x and c != col_color and pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break
if not has_score:
    for c in df.columns:
        if c not in (col_x, col_y) and pd.api.types.is_numeric_dtype(df[c]):
            col_color = c
            has_score = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.set_facecolor('#ffffff')

if has_x and has_y and has_score:
    # 构建渐变色图
    if cmap_name and cmap_name in plt.colormaps():
        cmap = plt.get_cmap(cmap_name)
    else:
        cmap = LinearSegmentedColormap.from_list('gradient',
            [palette[0], palette[1]])

    score_min = df[col_color].min()
    score_max = df[col_color].max()
    norm = Normalize(vmin=score_min, vmax=score_max)

    x_pos = np.arange(len(df))
    bar_width = 0.7

    for i, (_, row) in enumerate(df.iterrows()):
        color = cmap(norm(row[col_color]))
        ax.bar(i, row[col_y], bar_width, color=color,
               edgecolor='#ffffff', linewidth=0.3, alpha=alpha)

    # 色标
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, label=colorbar_label)
    cbar.ax.tick_params(labelsize=font_size - 1)
    cbar.set_label(colorbar_label, fontsize=font_size)

    # 标签
    ax.set_xticks(x_pos)
    ax.set_xticklabels(df[col_x].tolist(), rotation=45, ha='right', fontsize=font_size - 1)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)
    ax.tick_params(axis='y', labelsize=font_size - 1)
    ax.grid(axis='y', alpha=0.3)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面提示
    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x, y, color)',
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
