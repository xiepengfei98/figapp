#!/usr/bin/env python3
"""
韦恩图 (Venn Diagram) — Python 版本
======================================

【图表涵义】
韦恩图用重叠圆展示两个或三个集合之间的共有和特有元素。
集合用圆表示，重叠区域表示交集。

【适用场景】
- 基因集的重叠比较
- 差异表达基因的共有/特有分析
- 多个集合的交集展示

【数据要求】
- x: 集合名称（分类）
- y: 元素/成员（分类）

=== 列名映射 (columns) =======================================================
  x       — 集合名称（分类）
  y       — 元素/成员（分类）
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
from matplotlib.patches import Circle
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
# 4. 列名映射 — 按列顺序: 第1列=x(集合名称), 第2列=y(元素/成员), 第3列=facet(分面列,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_facet = _df_cols[2] if len(_df_cols) > 2 else None
col_group = col_color = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Venn Diagram | 图表标题
# @PARAM fig_width: float = 8 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM color_1: str = #E64B35 | 集合 1 颜色
# @PARAM color_2: str = #4DBBD5 | 集合 2 颜色
# @PARAM color_3: str = #00A087 | 集合 3 颜色

title    = str(params.get('title', 'Venn Diagram'))
fig_width  = float(params.get('fig_width', 8))
fig_height = float(params.get('fig_height', 8))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
color_1    = str(params.get('color_1', '#E64B35'))
color_2    = str(params.get('color_2', '#4DBBD5'))
color_3    = str(params.get('color_3', '#00A087'))

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

# --- 构建集合 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.set_aspect('equal')
ax.axis('off')

if has_x and has_y:
    sets_dict = {s: set(df[df[col_x] == s][col_y])
                 for s in df[col_x].unique()}
    names = list(sets_dict.keys())[:3]
    sets = [sets_dict[n] for n in names]
    colors = [color_1, color_2, color_3]

    if len(sets) == 2:
        a, b = sets
        cx = [-0.3, 0.3]
        r = 0.5

        for i in range(2):
            ax.add_patch(Circle((cx[i], 0), r, color=colors[i],
                                alpha=0.3, ec=colors[i], linewidth=2))
            ax.text(cx[i] - (0.4 if i == 0 else -0.4), 0, names[i],
                    fontsize=font_size, ha='center', va='center')

        ax.text(-0.45, 0, str(len(a - b)),
                fontsize=font_size + 4, ha='center', va='center',
                fontweight='bold')
        ax.text(0.45, 0, str(len(b - a)),
                fontsize=font_size + 4, ha='center', va='center',
                fontweight='bold')
        ax.text(0, 0, str(len(a & b)),
                fontsize=font_size + 4, ha='center', va='center',
                fontweight='bold')

    elif len(sets) == 3:
        a, b, c = sets
        positions = [(0, 0.25), (0.25, -0.15), (-0.25, -0.15)]
        r = 0.42

        for i in range(3):
            ax.add_patch(Circle(positions[i], r, color=colors[i],
                                alpha=0.3, ec=colors[i], linewidth=2))
            px, py = positions[i]
            off = 0.55
            if i == 0:
                lp = (px, py + off)
            elif i == 1:
                lp = (px + off * 0.7, py - off * 0.5)
            else:
                lp = (px - off * 0.7, py - off * 0.5)
            ax.text(*lp, names[i], fontsize=font_size,
                    ha='center', va='center')

        ax.text(0, 0.45, str(len(a - b - c)), fontsize=font_size + 2,
                ha='center', va='center', fontweight='bold')
        ax.text(0.35, -0.4, str(len(b - a - c)), fontsize=font_size + 2,
                ha='center', va='center', fontweight='bold')
        ax.text(-0.35, -0.4, str(len(c - a - b)), fontsize=font_size + 2,
                ha='center', va='center', fontweight='bold')
        ax.text(0.22, 0.22, str(len((a & b) - c)), fontsize=font_size,
                ha='center', va='center', fontweight='bold')
        ax.text(-0.22, 0.22, str(len((a & c) - b)), fontsize=font_size,
                ha='center', va='center', fontweight='bold')
        ax.text(0, -0.25, str(len((b & c) - a)), fontsize=font_size,
                ha='center', va='center', fontweight='bold')
        ax.text(0, 0.02, str(len(a & b & c)), fontsize=font_size,
                ha='center', va='center', fontweight='bold')

    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

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
