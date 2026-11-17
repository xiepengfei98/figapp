#!/usr/bin/env python3
"""
饼图矩阵 (Pie Chart Matrix) — Python 版本
============================================

【图表涵义】
饼图矩阵以网格布局展示多个饼图，行和列代表不同分组维度，
每个格子中的饼图展示该行列组合下的类别构成。

【适用场景】
- 双维度分组的类别构成比较
- 按行变量和列变量交叉展示比例数据
- 展示多维度交叉分析的组成结构

【数据要求】
- x: 类别变量（饼图扇形标签）
- y: 数值变量（扇形大小）
- group: 列分组变量（决定饼图在矩阵中的列位置）
- facet: 行分组变量（决定饼图在矩阵中的行位置）

=== 列名映射 (columns) =======================================================
  x       — 类别变量（分类，扇形标签）
  y       — 数值变量（数值，扇形大小）
  group   — 列分组变量（分类，矩阵列）
  facet   — 行分组变量（分类，矩阵行）
  color   — 额外类别区分（可选）

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
import matplotlib.gridspec as gridspec
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
# 4. 列名映射 — 按列顺序: 第1列=x(类别变量), 第2列=y(数值变量), 第3列=group(列分组), 第4列=facet(行分组)
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
# @PARAM show_pct: bool = true | 显示百分比
# @PARAM start_angle: float = 90 | 起始角度

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', ''))
y_label      = str(params.get('y_label', col_y or ''))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 8))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
show_pct     = str(params.get('show_pct', 'true')).lower() == 'true'
start_angle  = float(params.get('start_angle', 90))

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
has_facet = col_facet and col_facet in df.columns

if not has_x:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]) and c not in (col_group, col_facet):
            col_x = c
            has_x = True
            break
if not has_y:
    for c in df.columns:
        if c != col_x and pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break
if not has_group:
    for c in df.columns:
        if c != col_x and c != col_facet and not pd.api.types.is_numeric_dtype(df[c]):
            col_group = c
            has_group = True
            break
if not has_facet:
    for c in df.columns:
        if c not in (col_x, col_group) and not pd.api.types.is_numeric_dtype(df[c]):
            col_facet = c
            has_facet = True
            break

# --- 绘图 ---
if has_x and has_y and has_group and has_facet:
    row_vars = sorted(df[col_facet].unique())
    col_vars = sorted(df[col_group].unique())
    categories = sorted(df[col_x].unique())
    cat_colors = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}

    n_rows = len(row_vars)
    n_cols = len(col_vars)
    fig_width_adj = max(fig_width, n_cols * 2.5)
    fig_height_adj = max(fig_height, n_rows * 2.5)

    fig = plt.figure(figsize=(fig_width_adj, fig_height_adj))
    gs = gridspec.GridSpec(n_rows, n_cols, figure=fig, hspace=0.4, wspace=0.4)

    for i, row_var in enumerate(row_vars):
        for j, col_var in enumerate(col_vars):
            ax = fig.add_subplot(gs[i, j])
            sub = df[(df[col_facet] == row_var) & (df[col_group] == col_var)]
            sub = sub.sort_values(col_x)
            sub_colors = [cat_colors.get(cat, palette[0]) for cat in sub[col_x]]

            autopct_val = '%1.1f%%' if show_pct else None
            ax.pie(sub[col_y].values, labels=None,
                   autopct=autopct_val, startangle=start_angle,
                   colors=sub_colors[:len(sub)],
                   pctdistance=0.75, textprops={'fontsize': font_size - 3})
            if i == n_rows - 1:
                ax.set_xlabel(str(col_var), fontsize=font_size - 1)
            if j == 0:
                ax.set_ylabel(str(row_var), fontsize=font_size - 1)

    # 统一图例
    handles = [plt.Rectangle((0, 0), 1, 1, color=cat_colors[cat]) for cat in categories]
    fig.legend(handles, list(categories), title=col_x,
               loc='center left', bbox_to_anchor=(1.02, 0.5),
               fontsize=font_size - 1, title_fontsize=font_size)

    if title:
        fig.suptitle(title, fontsize=font_size + 2, fontweight='bold')

    fig.tight_layout(rect=[0, 0, 0.88, 0.95])

else:
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    missing = []
    if not has_x: missing.append('x')
    if not has_y: missing.append('y')
    if not has_group: missing.append('group')
    if not has_facet: missing.append('facet')
    ax.text(0.5, 0.5, f'请上传数据并配置列映射\n(columns → {", ".join(missing)})',
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
