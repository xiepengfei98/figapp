#!/usr/bin/env python3
"""
环形图 (Circle Plot / Polar Scatter) — Python 版本
===================================================

【图表涵义】
环形图在极坐标系中沿圆周排列数据点，每个点由径向线连接圆心，
适合展示周期性数据模式或为大量类别提供紧凑的可视化布局。

【适用场景】
- 展示各分类的数值在极坐标下的分布
- 周期性数据模式展示
- 替代常规条形图的紧凑可视化

【数据要求】
- x: 类别标识（分类）
- y: 数值变量（数值）

=== 列名映射 (columns) =======================================================
  x       — 类别标识
  y       — 数值变量（数值）
  group   — 分组变量（可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(类别标识), 第2列=y(数值变量), 第3列=group(分组,可选), 第4列=facet(可选)
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
# @PARAM point_size: float = 200 | 数据点大小
# @PARAM color_by_group: bool = false | 按分组着色
# @PARAM show_lines: bool = true | 显示从中心到点的连线

title          = str(params.get('title', ''))
fig_width      = float(params.get('fig_width', 8))
fig_height     = float(params.get('fig_height', 8))
dpi            = int(params.get('dpi', 300))
font_size      = int(params.get('font_size', 12))
point_size     = float(params.get('point_size', 200))
color_by_group = str(params.get('color_by_group', 'false')).lower() == 'true'
show_lines     = str(params.get('show_lines', 'true')).lower() == 'true'

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

has_group = col_group and col_group in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height),
                        subplot_kw=dict(polar=True))

if has_x and has_y:
    n = len(df)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    values = df[col_y].values

    for i, (_, row) in enumerate(df.iterrows()):
        angle = angles[i]
        val = row[col_y]

        if color_by_group and has_group:
            grp_idx = list(df[col_group].unique()).index(row[col_group])
            color = palette[grp_idx % len(palette)]
        else:
            color = palette[i % len(palette)]

        # 径向线
        if show_lines:
            ax.plot([angle, angle], [0, val], color=color, linewidth=1, alpha=0.7)

        # 数据点
        ax.scatter(angle, val, s=point_size, color=color,
                   zorder=5, edgecolors='white', linewidth=0.5)

    # 类别标签
    ax.set_xticks(angles)
    ax.set_xticklabels(df[col_x], fontsize=font_size - 3)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=20)

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
