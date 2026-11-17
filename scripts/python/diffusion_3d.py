#!/usr/bin/env python3
"""
3D 扩散映射图 (3D Diffusion Map) — Python 版本
=================================================

【图表涵义】
3D 扩散映射图展示高维数据的 3 个扩散主成分（DC1/DC2/DC3），
以三维散点呈现样本聚类结构，支持分组着色。

【适用场景】
- 高维数据的三维降维展示
- 单细胞数据的 3D 扩散映射
- 复杂数据结构的 3D 探索

【数据要求】
- x: DC1 坐标（数值）
- y: DC2 坐标（数值）
- color: DC3 坐标（数值）
- group: 分组变量（分类，可选）

=== 列名映射 (columns) =======================================================
  x       — DC1（数值）
  y       — DC2（数值）
  color   — DC3（数值）
  group   — 分组变量（分类，可选）
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
from mpl_toolkits.mplot3d import Axes3D
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
# 4. 列名映射 — 按列顺序: 第1列=x(DC1), 第2列=y(DC2), 第3列=color(DC3), 第4列=group(可选), 第5列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_color = _df_cols[2] if len(_df_cols) > 2 else None
col_group = _df_cols[3] if len(_df_cols) > 3 else None
col_facet = _df_cols[4] if len(_df_cols) > 4 else None
col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = 3D Diffusion Map | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM point_size: float = 40 | 点大小
# @PARAM alpha: float = 0.85 | 透明度
# @PARAM elev: float = 25 | 仰角
# @PARAM azim: float = -60 | 方位角

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 6))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
point_size = float(params.get('point_size', 40))
alpha      = float(params.get('alpha', 0.85))
elev       = float(params.get('elev', 25))
azim       = float(params.get('azim', -60))

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
has_z = col_color and col_color in df.columns
has_group = col_group and col_group in df.columns

# --- 绘图 ---
if has_x and has_y and has_z:
    fig = plt.figure(figsize=(fig_width, fig_height))
    ax = fig.add_subplot(111, projection='3d')

    if has_group:
        for i, grp in enumerate(df[col_group].unique()):
            sub = df[df[col_group] == grp]
            ax.scatter(sub[col_x], sub[col_y], sub[col_color],
                       c=palette[i % len(palette)], label=str(grp),
                       s=point_size, alpha=alpha,
                       edgecolors='#333333', linewidths=0.5)
        ax.legend(fontsize=font_size - 1, loc='upper right')
    else:
        ax.scatter(df[col_x], df[col_y], df[col_color],
                   c=palette[0], s=point_size, alpha=alpha,
                   edgecolors='#333333', linewidths=0.5)

    ax.set_xlabel(col_x, fontsize=font_size, labelpad=8)
    ax.set_ylabel(col_y, fontsize=font_size, labelpad=8)
    ax.set_zlabel(col_color, fontsize=font_size, labelpad=8)
    ax.view_init(elev=elev, azim=azim)
    ax.tick_params(labelsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

else:
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x=DC1, y=DC2, color=DC3)',
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
