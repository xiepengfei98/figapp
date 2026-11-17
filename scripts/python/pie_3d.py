#!/usr/bin/env python3
"""
三维饼图 (3D Pie Chart) — Python 版本
========================================

【图表涵义】
三维饼图在传统饼图基础上添加阴影和突出效果，增强立体感和视觉冲击力，
适合强调最大类别或在报告中作为视觉焦点。

【适用场景】
- 展示分类数据的比例构成，强调最大类别
- 报告或演示中需要更高视觉吸引力的场景
- 替代标准饼图，增加立体效果

【数据要求】
- x: 类别变量（分类）
- y: 数值变量（数值）

=== 列名映射 (columns) =======================================================
  x       — 类别变量（分类，扇形标签）
  y       — 数值变量（数值，扇形大小）
  group   — 二级分组（可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(类别变量), 第2列=y(数值变量), 第3列=facet(可选)
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
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM show_pct: bool = true | 显示百分比
# @PARAM start_angle: float = 90 | 起始角度
# @PARAM explode_first: bool = true | 突出第一个扇区
# @PARAM explode_dist: float = 0.08 | 扇区突出距离

title          = str(params.get('title', ''))
fig_width      = float(params.get('fig_width', 10))
fig_height     = float(params.get('fig_height', 7))
dpi            = int(params.get('dpi', 300))
font_size      = int(params.get('font_size', 12))
show_pct       = str(params.get('show_pct', 'true')).lower() == 'true'
start_angle    = float(params.get('start_angle', 90))
explode_first  = str(params.get('explode_first', 'true')).lower() == 'true'
explode_dist   = float(params.get('explode_dist', 0.08))

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

if not has_x:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break
if not has_y:
    for c in df.columns:
        if c != col_x and pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    values = df[col_y].values
    labels = df[col_x].tolist()
    n = len(df)

    # 扇区颜色
    pie_colors = [palette[i % len(palette)] for i in range(n)]

    # 突出效果
    explode = [explode_dist] * n
    if explode_first and n > 0:
        explode[0] = explode_dist * 3

    autopct_val = '%1.1f%%' if show_pct else None
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct=autopct_val, startangle=start_angle,
        colors=pie_colors, explode=explode, shadow=True,
        pctdistance=0.8, textprops={'fontsize': font_size - 1},
        wedgeprops={'edgecolor': 'white', 'linewidth': 0.8})

    # 图例
    ax.legend(wedges, labels, title=col_x, loc='center left',
              bbox_to_anchor=(1, 0, 0.5, 1), fontsize=font_size - 1,
              title_fontsize=font_size)

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
