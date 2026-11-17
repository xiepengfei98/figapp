#!/usr/bin/env python3
"""
诺莫图逻辑回归 (Nomogram for Logistic Regression) — Python 版本
===============================================================

【图表涵义】
诺莫图逻辑回归用图形化方式展示 Logistic 回归预测模型，每个预测变量
对应一个评分轴，总分映射到预测概率。

【适用场景】
- Logistic 回归预测模型的可视化
- 临床预测模型的评分工具
- 展示各变量对预测结果的贡献

【数据要求】
- x: 变量类型（"predictor" 或 "axis"）
- y: 变量名称（分类）
- group: 变量水平（分类）
- size: 分数（数值）

=== 列名映射 (columns) =======================================================
  x       — 类型（"predictor"/"axis"）
  y       — 变量名称（分类）
  group   — 水平（分类）
  size    — 分数（数值）
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
# 4. 列名映射 — 按列顺序: 第1列=x(类型), 第2列=y(变量名称), 第3列=group(水平), 第4列=size(分数), 第5列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_size = _df_cols[3] if len(_df_cols) > 3 else None
col_facet = _df_cols[4] if len(_df_cols) > 4 else None
col_color = col_label = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Nomogram | 图表标题
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 10 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 12))
fig_height = float(params.get('fig_height', 10))
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
has_type = col_x and col_x in df.columns
has_var = col_y and col_y in df.columns
has_level = col_group and col_group in df.columns
has_pts = col_size and col_size in df.columns

# --- 绘图 ---
if has_type and has_var and has_level and has_pts:
    predictors = df[df[col_x] == 'predictor']
    vars_list = list(predictors[col_y].unique())
    total_rows = len(vars_list) + 2

    y_levels = {v: total_rows - i for i, v in enumerate(vars_list)}
    y_levels['Total_Points'] = 2
    y_levels['Probability'] = 1

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    predictor_color = palette[3] if len(palette) > 3 else '#3C5488'
    axis_color = palette[0]

    # 绘制每个预测变量的轴
    for var_name in vars_list:
        var_data = predictors[predictors[col_y] == var_name]
        y_pos = y_levels[var_name]

        min_pts = var_data[col_size].min()
        max_pts = var_data[col_size].max()
        pt_range = max_pts - min_pts if max_pts > min_pts else 1

        ax.plot([0.1, 0.9], [y_pos, y_pos], color=predictor_color, linewidth=1.5)

        for _, row in var_data.iterrows():
            x_frac = (row[col_size] - min_pts) / pt_range
            x_pos = 0.1 + x_frac * 0.8
            ax.text(x_pos, y_pos + 0.3, str(row[col_group]),
                    fontsize=font_size - 3, ha='center', va='bottom', color='#333333')

        ax.text(0.02, y_pos, str(var_name).replace('_', ' '),
                fontsize=font_size - 1, ha='left', va='center',
                fontweight='bold', color='#333333')

    # Total Points 轴
    total_y = y_levels['Total_Points']
    ax.plot([0.1, 0.9], [total_y, total_y], color=predictor_color, linewidth=1.5)
    for i, pts in enumerate(range(0, 301, 50)):
        x_pos = 0.1 + (i / 6) * 0.8
        ax.text(x_pos, total_y - 0.3, str(pts),
                fontsize=font_size - 3, ha='center', va='top', color=axis_color)
    ax.text(0.02, total_y, 'Total Points', fontsize=font_size - 1,
            ha='left', va='center', fontweight='bold', color='#333333')

    # Probability 轴
    prob_y = y_levels['Probability']
    ax.plot([0.1, 0.9], [prob_y, prob_y], color=predictor_color, linewidth=1.5)
    for i, pv in enumerate([0.01, 0.05, 0.10, 0.20, 0.35, 0.55, 0.75]):
        x_pos = 0.1 + (i / 6) * 0.8
        ax.text(x_pos, prob_y - 0.3, f'{pv:.2f}',
                fontsize=font_size - 3, ha='center', va='top', color=axis_color)
    ax.text(0.02, prob_y, 'Risk Probability', fontsize=font_size - 1,
            ha='left', va='center', fontweight='bold', color='#333333')

    ax.set_xlim(0, 1)
    ax.set_ylim(0.5, total_rows + 0.5)
    ax.axis('off')

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

else:
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x=type, y=variable, group=level, size=points)',
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
