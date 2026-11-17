#!/usr/bin/env python3
"""
线图误差线 (Line Chart with Error Bands) — Python 版本
=======================================================

【图表涵义】
线图误差线在线图基础上用半透明色带表示数据的上下界范围，
直观展示数据的波动区间和变化趋势。

【适用场景】
- 展示时间序列数据的波动范围
- 展示预测区间或置信区间
- 需要同时展示趋势和方差信息的场景

【数据要求】
- x: X 轴变量（数值或有序）
- y: Y 轴中值变量（数值）
- label: 下界变量（数值，填充区间下限）
- group: 上界变量（数值，填充区间上限）
- color: 分组变量（分类，可选，不同颜色区分）

=== 列名映射 (columns) =======================================================
  x       — X 轴变量（数值或有序）
  y       — Y 轴中值（数值）
  label   — 下界（数值，填充区间下限）
  group   — 上界（数值，填充区间上限）
  color   — 分组变量（分类，可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(X轴), 第2列=y(中值), 第3列=label(下界), 第4列=group(上界), 第5列=color(分组,可选), 第6列=facet(分面,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_label = _df_cols[2] if len(_df_cols) > 2 else None
col_group = _df_cols[3] if len(_df_cols) > 3 else None
col_color = _df_cols[4] if len(_df_cols) > 4 else None
col_facet = _df_cols[5] if len(_df_cols) > 5 else None
col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.25 | 填充色带透明度
# @PARAM line_width: float = 1.0 | 线宽
# @PARAM show_legend: bool = true | 显示图例

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', col_x or ''))
y_label      = str(params.get('y_label', col_y or ''))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 6))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
alpha        = float(params.get('alpha', 0.25))
line_width   = float(params.get('line_width', 1.0))
show_legend  = str(params.get('show_legend', 'true')).lower() == 'true'

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
has_low = col_label and col_label in df.columns
has_high = col_group and col_group in df.columns
has_color_grp = col_color and col_color in df.columns

if not has_x:
    for c in df.columns:
        col_x = c
        has_x = True
        break
if not has_y:
    for c in df.columns:
        if c != col_x and pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break
if not has_low:
    for c in df.columns:
        if c not in (col_x, col_y) and pd.api.types.is_numeric_dtype(df[c]):
            col_label = c
            has_low = True
            break
if not has_high:
    for c in df.columns:
        if c not in (col_x, col_y, col_label) and pd.api.types.is_numeric_dtype(df[c]):
            col_group = c
            has_high = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_low and has_high:
    if has_color_grp:
        groups = sorted(df[col_color].unique())
        for i, grp in enumerate(groups):
            d = df[df[col_color] == grp].sort_values(col_x)
            color = palette[i % len(palette)]
            ax.fill_between(d[col_x], d[col_label], d[col_group],
                            color=color, alpha=alpha)
            ax.plot(d[col_x], d[col_y], linewidth=line_width, color=color, label=str(grp))
    else:
        d = df.sort_values(col_x)
        ax.fill_between(d[col_x], d[col_label], d[col_group],
                        color=palette[0], alpha=alpha)
        ax.plot(d[col_x], d[col_y], linewidth=line_width, color=palette[0])

    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)
    ax.tick_params(axis='both', labelsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if has_color_grp and show_legend:
        ax.legend(fontsize=font_size - 1)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x, y, label, group)',
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
