#!/usr/bin/env python3
"""
交互式火山图 (Interactive Volcano Plot) — Python 版本
=====================================================

【图表涵义】
交互式火山图展示差异表达分析结果，标记显著上/下调基因并标注名称，
支持提取和展示关键差异基因。

【适用场景】
- 差异表达基因的展示和标注
- 需要突出显示特定基因的火山图
- 基因筛选和标记的交互式展示

【数据要求】
- x: log2 Fold Change（数值）
- y: -log10(p-value)（数值）
- group: 显著性分组（分类，如 Up/Down/NS）
- label: 基因名（分类）
- color: 是否标注（布尔，可选）

=== 列名映射 (columns) =======================================================
  x       — log2FC（数值）
  y       — -log10(p-value)（数值）
  group   — 显著性（分类）
  label   — 基因名（分类）
  color   — 标注标记（布尔，可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(log2FC), 第2列=y(-log10p), 第3列=group(显著性), 第4列=label(基因名), 第5列=color(标注标记)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_label = _df_cols[3] if len(_df_cols) > 3 else None
col_color = _df_cols[4] if len(_df_cols) > 4 else None
col_facet = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Volcano Plot | 图表标题
# @PARAM x_label: str = log2 Fold Change | X 轴标签
# @PARAM y_label: str = -log10(p-value) | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.7 | 点透明度
# @PARAM lfc_threshold: float = 1 | log2FC 阈值
# @PARAM p_threshold: float = 0.01 | p-value 阈值

title          = str(params.get('title', ''))
x_label        = str(params.get('x_label', 'log2 Fold Change'))
y_label        = str(params.get('y_label', '-log10(p-value)'))
fig_width      = float(params.get('fig_width', 10))
fig_height     = float(params.get('fig_height', 8))
dpi            = int(params.get('dpi', 300))
font_size      = int(params.get('font_size', 12))
alpha          = float(params.get('alpha', 0.7))
lfc_threshold  = float(params.get('lfc_threshold', 1))
p_threshold    = float(params.get('p_threshold', 0.01))
neg_log_p_thr  = -np.log10(p_threshold)

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
has_fc = col_x and col_x in df.columns
has_pv = col_y and col_y in df.columns
has_sig = col_group and col_group in df.columns
has_gene = col_label and col_label in df.columns
has_label_flag = col_color and col_color in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_fc and has_pv:
    sig_colors = {'Up': palette[0], 'Down': palette[1], 'NS': '#999999'}

    if has_label_flag:
        if df[col_color].dtype == bool:
            labeled = df[df[col_color] == True]
            unlabeled = df[df[col_color] != True]
        else:
            flag_str = df[col_color].astype(str).str.lower()
            labeled = df[flag_str == 'true']
            unlabeled = df[flag_str != 'true']
    else:
        labeled = pd.DataFrame()
        unlabeled = df

    # 未标注点
    if has_sig:
        for sig in ['NS', 'Down', 'Up']:
            mask = unlabeled[col_group] == sig
            if mask.sum() == 0:
                continue
            sub = unlabeled[mask]
            point_alpha = 0.3 if sig == 'NS' else alpha
            point_size = 30 if sig == 'NS' else 80
            ax.scatter(sub[col_x], sub[col_y], s=point_size, alpha=point_alpha,
                       color=sig_colors.get(sig, '#999999'),
                       edgecolors='none', label='' if sig == 'NS' else sig)
    else:
        ax.scatter(unlabeled[col_x], unlabeled[col_y], s=30, alpha=0.3,
                   color='#999999', edgecolors='none')

    # 标注点
    if len(labeled) > 0 and has_sig:
        for sig in ['Down', 'Up']:
            mask = labeled[col_group] == sig
            if mask.sum() == 0:
                continue
            sub = labeled[mask]
            ax.scatter(sub[col_x], sub[col_y], s=120,
                       color=sig_colors.get(sig, '#999999'),
                       edgecolors='#333333', linewidths=0.5, zorder=5)

    # 基因标签
    if has_gene and len(labeled) > 0:
        for _, row in labeled.iterrows():
            ax.annotate(str(row[col_label]), (row[col_x], row[col_y]),
                        fontsize=font_size - 3, color='#333333',
                        xytext=(5, 5), textcoords='offset points',
                        arrowprops=dict(arrowstyle='-', color='#cccccc', lw=0.3))

    # 阈值线
    ax.axhline(y=neg_log_p_thr, color='#666666', linestyle='--', linewidth=0.8)
    ax.axvline(x=-lfc_threshold, color='#666666', linestyle='--', linewidth=0.8)
    ax.axvline(x=lfc_threshold, color='#666666', linestyle='--', linewidth=0.8)

    # 图例
    if has_sig:
        handles = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor=palette[0],
                   markersize=8, label='Up-regulated'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=palette[1],
                   markersize=8, label='Down-regulated'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#999999',
                   markersize=6, label='Not Significant'),
        ]
        ax.legend(handles=handles, fontsize=font_size - 1, loc='upper right')

    ax.set_xlabel(x_label, fontsize=font_size)
    ax.set_ylabel(y_label, fontsize=font_size)
    ax.tick_params(labelsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x=log2FC, y=-log10(p), group=significance, label=gene)',
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
