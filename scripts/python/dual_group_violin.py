#!/usr/bin/env python3
"""
双分组小提琴图 (Dual-Group Violin Plot) — Python 版本
======================================================

【图表涵义】
双分组小提琴图展示两个分组变量交叉下的数据分布，如 Male/Female 在不同
类别中的分布，每个类别内子组用不同颜色的小提琴并列展示。

【适用场景】
- 展示两个分类变量交叉下的数值分布
- 比如此较不同性别在多个条件下的表达量分布
- 展示组间和组内变异

【数据要求】
- x: 主类别变量（分类）
- y: 数值变量（数值）
- group: 子分组变量（分类，如性别）

=== 列名映射 (columns) =======================================================
  x       — 主类别变量（分类）
  y       — 数值变量（数值）
  group   — 子分组变量（分类，决定颜色）
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
from matplotlib.patches import Patch
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
# 4. 列名映射 — 按列顺序: 第1列=x(主类别), 第2列=y(数值), 第3列=group(子分组), 第4列=facet(可选)
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
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.55 | 小提琴透明度
# @PARAM show_box: bool = true | 显示箱线图

title       = str(params.get('title', ''))
x_label     = str(params.get('x_label', col_x or ''))
y_label     = str(params.get('y_label', col_y or ''))
fig_width   = float(params.get('fig_width', 12))
fig_height  = float(params.get('fig_height', 6))
dpi         = int(params.get('dpi', 300))
font_size   = int(params.get('font_size', 12))
alpha       = float(params.get('alpha', 0.55))
show_box    = str(params.get('show_box', 'true')).lower() == 'true'

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

if not has_x:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]) and c != col_group:
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
        if not pd.api.types.is_numeric_dtype(df[c]) and c != col_x:
            col_group = c
            has_group = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_group:
    categories = sorted(df[col_x].unique())
    subgroups = sorted(df[col_group].unique())
    sub_colors = {sg: palette[i % len(palette)] for i, sg in enumerate(subgroups)}

    # 位置映射：每个 (cat, subgroup) 有略为偏移的 x 坐标
    offset = 0.17
    pos_map = {}
    for i, cat in enumerate(categories):
        for j, sg in enumerate(subgroups):
            pos_map[(cat, sg)] = i + (j - (len(subgroups) - 1) / 2) * offset * 2

    for cat in categories:
        for sg in subgroups:
            vals = df[(df[col_x] == cat) & (df[col_group] == sg)][col_y].dropna().values
            pos = pos_map[(cat, sg)]
            if len(vals) > 1:
                vp = ax.violinplot(vals, positions=[pos], showmeans=False,
                                   showmedians=False, showextrema=False)
                for body in vp['bodies']:
                    body.set_facecolor(sub_colors[sg])
                    body.set_alpha(alpha)
                    body.set_edgecolor('#333333')
                    body.set_linewidth(0.5)

                if show_box:
                    ax.boxplot(vals, positions=[pos], widths=0.1, patch_artist=True,
                               manage_ticks=False, showfliers=True,
                               boxprops=dict(facecolor=sub_colors[sg], alpha=min(alpha + 0.15, 1.0),
                                             edgecolor='#333333', linewidth=0.8),
                               whiskerprops=dict(color='#333333', linewidth=0.8),
                               capprops=dict(color='#333333', linewidth=0.8),
                               medianprops=dict(color='#333333', linewidth=1.5),
                               flierprops=dict(marker='o', markerfacecolor=sub_colors[sg],
                                              markersize=4, markeredgecolor='#333333',
                                              markeredgewidth=0.5))

    # 图例
    legend_elements = [Patch(facecolor=sub_colors[sg], alpha=0.7, label=str(sg))
                       for sg in subgroups]
    ax.legend(handles=legend_elements, fontsize=font_size - 1, loc='upper right')

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, fontsize=font_size - 1)
    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)
    ax.tick_params(axis='y', labelsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x, y, group)',
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
