#!/usr/bin/env python3
"""
多序列比对 (Multiple Sequence Alignment) — Python 版本
=======================================================

【图表涵义】
多序列比对堆积条形图展示每个比对位置上各核苷酸（A/C/G/T）的频率分布，
顶部/底部标注共识序列，直观呈现序列保守性。

【适用场景】
- 展示多序列比对结果的保守性
- 展示每个位点的核苷酸频率
- 序列 motif 的保守性分析

【数据要求】
数据需包含每个位点的 A/C/G/T 频率和 consensus 标签。
- x: 比对位置列（数值或有序）
- y: A 碱基频率（数值，0-1）
- group: C 碱基频率（数值，0-1）
- label: G 碱基频率（数值，0-1）
- color: T 碱基频率（数值，0-1）
- size: consensus 碱基（分类，每个位点的共识碱基）

=== 列名映射 (columns) =======================================================
  x       — 位置列（数值/有序）
  y       — A 频率（数值）
  group   — C 频率（数值）
  label   — G 频率（数值）
  color   — T 频率（数值）
  size    — consensus 碱基（分类）

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
# 4. 列名映射 — 按列顺序: 第1列=x(位置), 第2列=y(A频率), 第3列=group(C频率), 第4列=label(G频率), 第5列=color(T频率), 第6列=size(consensus碱基), 第7列=facet(分面,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_label = _df_cols[3] if len(_df_cols) > 3 else None
col_color = _df_cols[4] if len(_df_cols) > 4 else None
col_size = _df_cols[5] if len(_df_cols) > 5 else None
col_facet = _df_cols[6] if len(_df_cols) > 6 else None
col_subgroup = None


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

title     = str(params.get('title', ''))
x_label   = str(params.get('x_label', 'Alignment Position'))
y_label   = str(params.get('y_label', 'Frequency'))
fig_width = float(params.get('fig_width', 12))
fig_height = float(params.get('fig_height', 6))
dpi       = int(params.get('dpi', 300))
font_size = int(params.get('font_size', 12))

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

# 核苷酸频率列
nt_map = {}
for nt, col_var in [('A', col_y), ('C', col_group), ('G', col_label), ('T', col_color)]:
    if col_var and col_var in df.columns:
        nt_map[nt] = col_var

has_consensus = col_size and col_size in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and len(nt_map) > 0:
    positions = df[col_x].values
    x_idx = np.arange(len(positions))
    bar_width = 0.8

    # 碱基颜色
    nt_colors = {'A': palette[0], 'C': palette[1], 'G': palette[2], 'T': palette[3]}

    # 堆积条形图
    nucleotides = ['A', 'C', 'G', 'T']
    bottoms = np.zeros(len(positions))

    for nt in nucleotides:
        if nt in nt_map:
            freqs = df[nt_map[nt]].values
            ax.bar(x_idx, freqs, bar_width, bottom=bottoms, color=nt_colors.get(nt, '#999999'),
                   edgecolor='white', linewidth=0.5, label=nt, zorder=3)
            bottoms += freqs

    # Consensus 标签
    if has_consensus:
        for i, pos in enumerate(positions):
            consensus = df[df[col_x] == pos][col_size].values
            if len(consensus) > 0:
                ax.text(i, -0.04, str(consensus[0]), ha='center', va='top',
                        fontsize=font_size + 2, fontweight='bold', color='#4d4d4d')

    ax.set_xticks(x_idx)
    ax.set_xticklabels([str(p) for p in positions], fontsize=font_size - 1)
    ax.set_xlabel(x_label, fontsize=font_size)
    ax.set_ylabel(y_label, fontsize=font_size)
    ax.set_ylim(-0.08, 1.02)
    ax.set_yticks(np.arange(0, 1.01, 0.25))
    ax.set_yticklabels([f'{y:.0%}' for y in np.arange(0, 1.01, 0.25)], fontsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=15)

    ax.legend(fontsize=font_size - 1, loc='upper right', frameon=True)
    ax.set_xlim(-0.5, len(positions) - 0.5)
    sns.despine()

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x, y/group/label/color 为 A/C/G/T 频率)',
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
