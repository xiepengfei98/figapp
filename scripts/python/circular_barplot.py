#!/usr/bin/env python3
"""
径向柱状图 (Circular / Radial Barplot) — Python 版本
=====================================================

【图表涵义】
径向柱状图使用极坐标展示类别比较，环形布局将柱形围绕圆心排列，
视觉冲击力强，适合展示周期性数据或大量类别的比较。

【适用场景】
- 展示大量类别的数值比较，节省横向空间
- 周期性数据（如月份、时间点）的直观展示
- 需要视觉冲击力的报告或展示场景

【数据要求】
- x: 类别变量，如基因名称、月份等（分类）
- y: 数值变量，如表达量、频率等（数值）
- group: 分组变量（可选），按组合色

=== 列名映射 (columns) =======================================================
  x       — 类别变量（分类，作为柱形标签）
  y       — 数值变量（数值，柱形高度）
  group   — 分组变量（可选，用于颜色区分）
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
from matplotlib.patches import Patch


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
# 4. 列名映射 — 按列顺序: 第1列=x(类别变量), 第2列=y(数值变量), 第3列=group(分组,可选), 第4列=facet(可选)
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
# @PARAM fig_width: float = 8 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.85 | 柱形透明度
# @PARAM sort_bars: bool = true | 按数值排序
# @PARAM sort_ascending: bool = false | 升序排列
# @PARAM hollow_center: bool = false | 环形（中心留空）
# @PARAM start_angle: int = 0 | 起始角度（度，0=12点方向）
# @PARAM show_values: bool = true | 显示数值标签
# @PARAM show_legend: bool = true | 显示图例

title         = str(params.get('title', ''))
fig_width     = float(params.get('fig_width', 8))
fig_height    = float(params.get('fig_height', 8))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 12))
alpha         = float(params.get('alpha', 0.85))
sort_bars     = str(params.get('sort_bars', 'true')).lower() == 'true'
sort_ascending = str(params.get('sort_ascending', 'false')).lower() == 'true'
hollow_center = str(params.get('hollow_center', 'false')).lower() == 'true'
start_angle   = int(params.get('start_angle', 0))
show_values   = str(params.get('show_values', 'true')).lower() == 'true'
show_legend   = str(params.get('show_legend', 'true')).lower() == 'true'


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
fig, ax = plt.subplots(figsize=(fig_width, fig_height),
                       subplot_kw={'projection': 'polar'})

if has_x and has_y:
    plot_data = df[[col_x, col_y]].dropna().copy()
    if col_group and col_group in df.columns:
        plot_data[col_group] = df.loc[plot_data.index, col_group]

    # 排序
    if sort_bars:
        plot_data = plot_data.sort_values(col_y, ascending=sort_ascending)
        plot_data = plot_data.reset_index(drop=True)

    has_group = col_group and col_group in plot_data.columns
    n = len(plot_data)

    # 角度
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    start_rad = np.deg2rad(start_angle)
    angles = angles + start_rad
    width = 2 * np.pi / n

    # 柱形高度和底部
    values = plot_data[col_y].values
    bottom = 0
    if hollow_center:
        bottom = 0.3 * values.max()

    # 绘制柱形
    if has_group:
        unique_groups = plot_data[col_group].unique()
        for i, (_, row) in enumerate(plot_data.iterrows()):
            g = row[col_group]
            g_idx = list(unique_groups).index(g)
            color = palette[g_idx % len(palette)]
            ax.bar(angles[i], row[col_y], width=width, bottom=bottom,
                   color=color, alpha=alpha, edgecolor='white', linewidth=0.3)
    else:
        ax.bar(angles, values, width=width, bottom=bottom,
               color=palette[0], alpha=alpha, edgecolor='white', linewidth=0.3)

    # 数值标签
    if show_values:
        for i, (angle, val) in enumerate(zip(angles, values)):
            label_y = val + values.max() * 0.02
            ax.text(angle, label_y + bottom, f'{val:.1f}',
                    ha='center', va='bottom', fontsize=font_size - 3)

    # 分类标签
    ax.set_xticks(angles)
    ax.set_xticklabels(plot_data[col_x].values, fontsize=font_size - 4)

    # Y 轴
    ax.set_yticks([])
    ax.set_ylim(bottom, values.max() * 1.15)
    ax.grid(True, linestyle='--', alpha=0.3)

    # 图例
    if has_group and show_legend:
        legend_elements = []
        for i, g in enumerate(unique_groups):
            legend_elements.append(
                Patch(facecolor=palette[i % len(palette)], alpha=alpha, label=str(g)))
        ax.legend(handles=legend_elements, fontsize=font_size - 2,
                 loc='upper right', bbox_to_anchor=(1.3, 1.1))

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=25)

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
