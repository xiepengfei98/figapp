#!/usr/bin/env python3
"""
元分析亚组比较 (Meta-Analysis Subgroup Forest Plot) — Python 版本
================================================================

【图表涵义】
元分析亚组比较森林图展示各亚组内研究的效应量及亚组合并效应，
不同亚组用不同颜色区分，包含亚组汇总菱形。

【适用场景】
- Meta 分析中的亚组分析
- 比较不同亚组间的效应差异
- 展示亚组内各研究和合并结果

【数据要求】
- x: 研究名称（分类）
- y: 效应量估计值（数值）
- label: 置信区间下限（数值）
- color: 置信区间上限（数值）
- group: 亚组名（分类）
- size: 是否为汇总行（bool）

=== 列名映射 (columns) =======================================================
  x       — 研究名称（分类）
  y       — 效应量（数值）
  label   — CI 下限（数值）
  color   — CI 上限（数值）
  group   — 亚组名（分类）
  size    — 汇总标记（bool）
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
from matplotlib.lines import Line2D
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
# 4. 列名映射 — 按列顺序: 第1列=x(研究名称), 第2列=y(效应量), 第3列=label(CI下限), 第4列=color(CI上限), 第5列=group(亚组名), 第6列=size(汇总标记), 第7列=facet(分面,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_label = _df_cols[2] if len(_df_cols) > 2 else None
col_color = _df_cols[3] if len(_df_cols) > 3 else None
col_group = _df_cols[4] if len(_df_cols) > 4 else None
col_size = _df_cols[5] if len(_df_cols) > 5 else None
col_facet = _df_cols[6] if len(_df_cols) > 6 else None
col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Meta-Analysis Subgroup | 图表标题
# @PARAM x_label: str = Effect Size (95% CI) | X 轴标签
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 9 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号

title      = str(params.get('title', ''))
x_label    = str(params.get('x_label', 'Effect Size (95% CI)'))
fig_width  = float(params.get('fig_width', 12))
fig_height = float(params.get('fig_height', 9))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))

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
has_study = col_x and col_x in df.columns
has_est = col_y and col_y in df.columns
has_ci_low = col_label and col_label in df.columns
has_ci_high = col_color and col_color in df.columns
has_subgroup = col_group and col_group in df.columns
has_summary = col_size and col_size in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_study and has_est and has_ci_low and has_ci_high and has_subgroup:
    if has_summary:
        summaries = df[df[col_size] == True]
        studies = df[df[col_size] != True]
    else:
        studies = df
        summaries = pd.DataFrame()

    subgroups = studies[col_group].unique()
    sub_colors = {sg: palette[i % len(palette)] for i, sg in enumerate(subgroups)}

    # 参考线
    ax.axvline(x=0, color='#666666', linestyle='--', linewidth=0.8)

    y_idx = 0
    y_positions = {}
    current_sg = None

    for sg in subgroups:
        sg_studies = studies[studies[col_group] == sg]
        if len(sg_studies) == 0:
            continue

        if current_sg is not None:
            y_idx -= 1  # 亚组间间隔

        current_sg = sg

        for _, row in sg_studies.iterrows():
            y_positions[row[col_x]] = y_idx
            color = sub_colors.get(row[col_group], '#999999')
            ax.errorbar(row[col_y], y_idx,
                        xerr=[[row[col_y] - row[col_label]],
                              [row[col_color] - row[col_y]]],
                        fmt='s', color=color, markersize=8,
                        capsize=3, linewidth=1.5,
                        markeredgecolor='white', markeredgewidth=0.5)
            y_idx -= 1

        # 亚组汇总行
        sg_sum = summaries[summaries[col_group] == sg]
        for _, row in sg_sum.iterrows():
            y_positions[row[col_x]] = y_idx
            ax.errorbar(row[col_y], y_idx,
                        xerr=[[row[col_y] - row[col_label]],
                              [row[col_color] - row[col_y]]],
                        fmt='D', color='#333333', markersize=12,
                        capsize=5, linewidth=2.5,
                        markeredgecolor='white', markeredgewidth=0.5)
            y_idx -= 1

    # 轴标签
    names = list(y_positions.keys())
    ys = [y_positions[k] for k in names]
    ax.set_yticks(ys)
    ax.set_yticklabels(names, fontsize=font_size - 1)
    ax.set_xlabel(x_label, fontsize=font_size)
    ax.tick_params(labelsize=font_size - 1)

    # 图例
    handles = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor=c,
               markersize=8, label=sg)
        for sg, c in sub_colors.items()
    ]
    handles.append(
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#333333',
               markersize=10, label='Summary')
    )
    ax.legend(handles=handles, loc='upper left', fontsize=font_size - 1,
              title=col_group)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

else:
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x=study, y=est, label=ci_low,\ncolor=ci_high, group=subgroup, size=is_summary)',
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
