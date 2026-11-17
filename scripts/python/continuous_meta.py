#!/usr/bin/env python3
"""
连续变量 Meta 分析森林图 (Continuous Meta-Analysis Forest Plot) — Python 版本
===========================================================================

【图表涵义】
连续变量 Meta 分析森林图展示多个研究的均数差（MD）和置信区间，
包含汇总菱形和权重百分比。

【适用场景】
- 连续型结局的 Meta 分析结果展示
- 均数差/标准化均数差的森林图
- 治疗组 vs 对照组的连续指标比较

【数据要求】
- x: 研究名称（分类）
- y: 治疗组均数（数值）
- group: 治疗组标准差（数值）
- label: 对照组均数（数值）
- color: 对照组标准差（数值）
- size: 权重（数值）
数据还需包含 treat_n 和 control_n 列

=== 列名映射 (columns) =======================================================
  x       — 研究名称（分类）
  y       — 治疗组均数（数值）
  group   — 治疗组标准差（数值）
  label   — 对照组均数（数值）
  color   — 对照组标准差（数值）
  size    — 权重（数值，可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(研究名称), 第2列=y(治疗组均数), 第3列=group(治疗组标准差), 第4列=label(对照组均数), 第5列=color(对照组标准差), 第6列=size(权重,可选), 第7列=facet(可选)
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

# @PARAM title: str = Continuous Meta-Analysis | 图表标题
# @PARAM x_label: str = Mean Difference | X 轴标签
# @PARAM fig_width: float = 13 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号

title      = str(params.get('title', ''))
x_label    = str(params.get('x_label', 'Mean Difference'))
fig_width  = float(params.get('fig_width', 13))
fig_height = float(params.get('fig_height', 8))
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
has_tm = col_y and col_y in df.columns
has_tsd = col_group and col_group in df.columns
has_cm = col_label and col_label in df.columns
has_csd = col_color and col_color in df.columns

# 自动检测样本量列
tn_col = None
cn_col = None
for c in df.columns:
    if 'treat_n' in c.lower() or ('treat' in c.lower() and c.split('_')[-1].lower() == 'n'):
        tn_col = c
    if 'control_n' in c.lower() or ('control' in c.lower() and c.split('_')[-1].lower() == 'n'):
        cn_col = c

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_study and has_tm and has_tsd and has_cm and has_csd and tn_col and cn_col:
    plot_df = df.iloc[::-1].reset_index(drop=True)

    # 计算均数差和 95% CI
    plot_df['md'] = plot_df[col_y] - plot_df[col_label]
    plot_df['se_md'] = np.sqrt(
        (plot_df[col_group] ** 2 / plot_df[tn_col]) +
        (plot_df[col_color] ** 2 / plot_df[cn_col])
    )
    plot_df['ci_l'] = plot_df['md'] - 1.96 * plot_df['se_md']
    plot_df['ci_u'] = plot_df['md'] + 1.96 * plot_df['se_md']

    # 权重
    has_weight = col_size and col_size in df.columns
    if has_weight:
        wt = plot_df[col_size].values
    else:
        wt = 1.0 / plot_df['se_md'].values ** 2
    plot_df['wt_pct'] = wt / wt.sum() * 100

    n_studies = len(plot_df)
    summary_y = n_studies + 1.5

    # 汇总（随机效应）
    w = 1.0 / plot_df['se_md'].values ** 2
    summary_md = np.sum(w * plot_df['md'].values) / np.sum(w)
    summary_se = 1.0 / np.sqrt(np.sum(w))
    summary_ci_l = summary_md - 1.96 * summary_se
    summary_ci_u = summary_md + 1.96 * summary_se

    # 参考线
    ax.axvline(x=0, linestyle='--', color='#7f7f7f', linewidth=0.8, zorder=1)

    # 误差线
    for i, row in plot_df.iterrows():
        ax.errorbar(x=row['md'], y=i + 1,
                    xerr=[[row['md'] - row['ci_l']], [row['ci_u'] - row['md']]],
                    fmt='none', ecolor='#666666', elinewidth=0.8, capsize=0, zorder=2)

    # 数据点
    sizes = plot_df['wt_pct'].values * 1.0 + 3
    ax.scatter(plot_df['md'], np.arange(1, n_studies + 1),
               s=sizes ** 1.8, c=palette[3],
               edgecolors='#1A4D8C', linewidths=0.5, zorder=3)

    # 标签
    max_x = plot_df['ci_u'].max()
    for i, row in plot_df.iterrows():
        ax.text(max_x + 1.5, i + 1,
                f"MD: {row['md']:.1f} [{row['ci_l']:.1f}, {row['ci_u']:.1f}]",
                ha='left', va='center', fontsize=font_size - 3, color='#4d4d4d')
        if has_weight:
            ax.text(max_x + 5.5, i + 1,
                    f"{row['wt_pct']:.1f}%",
                    ha='left', va='center', fontsize=font_size - 3, color='#999999')

    # 汇总菱形
    diamond_x = [summary_md, summary_ci_u, summary_md, summary_ci_l]
    diamond_y = [summary_y + 0.4, summary_y, summary_y - 0.4, summary_y]
    ax.fill(diamond_x, diamond_y, facecolor=palette[0], alpha=0.7,
            edgecolor='#8B0000', linewidth=0.8, zorder=4)

    # 汇总标签
    ax.text(max_x + 1.5, summary_y,
            f"Summary: MD={summary_md:.1f} [{summary_ci_l:.1f}, {summary_ci_u:.1f}]",
            ha='left', va='center', fontsize=font_size - 3,
            fontweight='bold', color=palette[0])

    # 轴刻度
    all_y = list(range(1, n_studies + 1)) + [summary_y]
    all_labels = list(plot_df[col_x]) + ['']
    ax.set_yticks(all_y)
    ax.set_yticklabels(all_labels, fontsize=font_size - 1)
    ax.set_ylim(0.3, n_studies + 2.2)
    ax.set_xlabel(x_label, fontsize=font_size)
    ax.tick_params(axis='x', labelsize=font_size - 1)

    # 汇总行标签
    ax.text(-0.05, summary_y, 'Summary', ha='right', va='center',
            fontsize=font_size - 1, fontweight='bold', color=palette[0],
            transform=ax.get_yaxis_transform())

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    sns.despine()

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x=study, y=treat_mean,\ngroup=treat_sd, label=control_mean,\ncolor=control_sd, size=weight)',
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
