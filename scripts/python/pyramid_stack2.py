#!/usr/bin/env python3
"""
金字塔堆叠图2 (Stacked Population Pyramid by Income) — Python 版本
===================================================================

【图表涵义】
金字塔堆叠图2按收入水平堆叠展示人口年龄-性别分布，区分 Low/Medium/High
三个收入层级在各年龄组中的构成。

【适用场景】
- 展示不同收入水平的人口结构
- 社会经济分层的人口年龄分布
- 交互分析收入、年龄、性别三维结构

【数据要求】
- x: 年龄组（分类）
- y: 人口数（数值）
- group: 性别列（Male/Female）
- color: 收入水平列（Low/Medium/High）

=== 列名映射 (columns) =======================================================
  x       — 年龄组（分类）
  y       — 人口数（数值）
  group   — 性别（分类）
  color   — 收入水平（分类）
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
# 4. 列名映射 — 按列顺序: 第1列=x(年龄组), 第2列=y(人口数), 第3列=group(性别), 第4列=color(收入水平), 第5列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_color = _df_cols[3] if len(_df_cols) > 3 else None
col_facet = _df_cols[4] if len(_df_cols) > 4 else None
col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Population Pyramid by Income | 图表标题
# @PARAM x_label: str = Population Count | X 轴标签
# @PARAM y_label: str = Age Group | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.8 | 柱体透明度

title      = str(params.get('title', 'Population Pyramid by Income'))
x_label    = str(params.get('x_label', 'Population Count'))
y_label    = str(params.get('y_label', 'Age Group'))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 7))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
alpha      = float(params.get('alpha', 0.8))

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
has_gender = col_group and col_group in df.columns
has_cat = col_color and col_color in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_gender and has_cat:
    age_groups = sorted(df[col_x].unique())
    y_pos = np.arange(len(age_groups))

    categories = sorted(df[col_color].unique())
    cat_colors = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}

    genders = df[col_group].unique()
    male_ref = [g for g in genders if str(g).lower()[0] == 'm']
    gender_male = male_ref[0] if male_ref else genders[0]
    gender_female = [g for g in genders if g != gender_male][0]

    male_data = df[df[col_group] == gender_male]
    female_data = df[df[col_group] == gender_female]

    male_bottom = np.zeros(len(age_groups))
    female_bottom = np.zeros(len(age_groups))

    for cat in categories:
        m_vals = np.array([
            male_data[(male_data[col_x] == a) & (male_data[col_color] == cat)][col_y].sum()
            for a in age_groups
        ])
        f_vals = np.array([
            female_data[(female_data[col_x] == a) & (female_data[col_color] == cat)][col_y].sum()
            for a in age_groups
        ])

        ax.barh(y_pos, -m_vals, 0.65, left=-male_bottom,
                color=cat_colors[cat], alpha=alpha, edgecolor='white', linewidth=0.3)
        ax.barh(y_pos, f_vals, 0.65, left=female_bottom,
                color=cat_colors[cat], alpha=alpha, edgecolor='white', linewidth=0.3)

        male_bottom += m_vals
        female_bottom += f_vals

    max_val = max(male_bottom.max(), female_bottom.max())
    ax.set_xlim(-max_val * 1.12, max_val * 1.12)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(age_groups, fontsize=font_size - 1)
    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(abs(x)), ',')))

    ax.set_xlabel(x_label, fontsize=font_size)
    ax.set_ylabel(y_label, fontsize=font_size)
    ax.tick_params(labelsize=font_size - 1)

    legend_elements = [Patch(facecolor=cat_colors[c], alpha=alpha, label=c)
                       for c in categories]
    ax.legend(handles=legend_elements, title=col_color,
              loc='upper right', fontsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

else:
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x, y, group=gender, color=category)',
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
