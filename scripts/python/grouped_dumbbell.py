#!/usr/bin/env python3
"""
分组哑铃图 (Grouped Dumbbell Chart) — Python 版本
====================================================

【图表涵义】
分组哑铃图用线段连接两个时间点的数值（前/后），通过不同颜色区分组别，
展示多组别在多个类别上的前后变化对比。

【适用场景】
- 展示实验前后测量值的变化
- 比较多组别在不同类别上的变化幅度
- 展示干预措施前后的效果对比

【数据要求】
- x: 类别变量（Y 轴分类标签）
- y: 后测数值变量（右侧点）
- label: 前测数值变量（左侧点）
- group: 分组变量（不同颜色，dodge 错开）

=== 列名映射 (columns) =======================================================
  x       — 类别变量（Y 轴分类标签）
  y       — 后测数值（右侧点）
  label   — 前测数值（左侧点）
  group   — 分组变量（颜色区分，dodge 错开）
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
# 4. 列名映射 — 按列顺序: 第1列=x(类别), 第2列=y(后测), 第3列=label(前测), 第4列=group(分组)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_label = _df_cols[2] if len(_df_cols) > 2 else None
col_group = _df_cols[3] if len(_df_cols) > 3 else None
col_color = col_facet = col_size = col_subgroup = None


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
# @PARAM alpha: float = 0.8 | 点透明度
# @PARAM point_size: float = 80 | 点大小
# @PARAM line_width: float = 2.5 | 连接线宽度
# @PARAM show_labels: bool = false | 在点上显示数值标签

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', ''))
y_label      = str(params.get('y_label', col_y or ''))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 7))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
alpha        = float(params.get('alpha', 0.8))
point_size   = float(params.get('point_size', 80))
line_width   = float(params.get('line_width', 2.5))
show_labels  = str(params.get('show_labels', 'false')).lower() == 'true'

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
has_label = col_label and col_label in df.columns
has_group = col_group and col_group in df.columns

if not has_x:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break
if not has_y:
    for c in df.columns:
        if c != col_x and c != col_label and pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break
if not has_label:
    for c in df.columns:
        if c != col_x and c != col_y and pd.api.types.is_numeric_dtype(df[c]):
            col_label = c
            has_label = True
            break
if not has_group:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]) and c != col_x:
            col_group = c
            has_group = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_label:
    categories = sorted(df[col_x].unique(), reverse=True)
    cat_positions = {cat: i for i, cat in enumerate(categories)}

    if has_group:
        groups = sorted(df[col_group].unique())
        n_groups = len(groups)
        dodge_width = 0.4
        group_offsets = {
            grp: (i - (n_groups - 1) / 2) * dodge_width / (n_groups - 1) if n_groups > 1 else 0
            for i, grp in enumerate(groups)
        }

        for i, grp in enumerate(groups):
            sub = df[df[col_group] == grp]
            color = palette[i % len(palette)]
            offset = group_offsets[grp]
            for _, row in sub.iterrows():
                y_base = cat_positions[row[col_x]] + offset
                before_val = row[col_label]
                after_val = row[col_y]
                ax.plot([before_val, after_val], [y_base, y_base],
                        color=color, linewidth=line_width,
                        solid_capstyle='round', zorder=2)
                ax.scatter(before_val, y_base, color=color, s=point_size,
                          zorder=3, edgecolors='white', linewidths=0.8, alpha=alpha)
                ax.scatter(after_val, y_base, color=color, s=point_size,
                          zorder=3, edgecolors='white', linewidths=0.8, alpha=alpha)
                if show_labels:
                    ax.text(before_val, y_base, f'{before_val:.1f}',
                            ha='right', va='bottom', fontsize=font_size - 2, color=color)
                    ax.text(after_val, y_base, f'{after_val:.1f}',
                            ha='left', va='bottom', fontsize=font_size - 2, color=color)
            ax.scatter([], [], color=color, s=point_size, label=str(grp))
    else:
        # 无分组：所有线用同色
        color = palette[0]
        for _, row in df.iterrows():
            y_base = cat_positions[row[col_x]]
            before_val = row[col_label]
            after_val = row[col_y]
            ax.plot([before_val, after_val], [y_base, y_base],
                    color=color, linewidth=line_width, solid_capstyle='round', zorder=2)
            ax.scatter(before_val, y_base, color=color, s=point_size,
                      zorder=3, edgecolors='white', linewidths=0.8, alpha=alpha)
            ax.scatter(after_val, y_base, color=color, s=point_size,
                      zorder=3, edgecolors='white', linewidths=0.8, alpha=alpha)

    # 标签
    ax.set_yticks(list(cat_positions.values()))
    ax.set_yticklabels(categories, fontsize=font_size - 1)
    ax.set_xlabel(x_label or col_y, fontsize=font_size)
    ax.set_ylabel(y_label or col_x, fontsize=font_size)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if has_group:
        legend = ax.legend(loc='lower right', fontsize=font_size - 1, frameon=True, title=col_group)
        legend.get_title().set_fontsize(font_size)

    # 分面提示
    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x, y, label)',
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
