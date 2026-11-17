#!/usr/bin/env python3
"""
火山图 (Volcano Plot) — Python 版本
======================================

【图表涵义】
火山图展示差异表达分析结果，以 log2FC 为横轴、-log10(p-value) 为纵轴，
识别显著上调和下调的基因。

【适用场景】
- 基因差异表达分析结果的可视化
- 转录组/蛋白组数据的显著基因筛选
- 比较两组间的表达变化

【数据要求】
- x: log2 差异倍数（log2FC，数值）
- y: p 值（数值）
- label: 基因名（可选）

=== 列名映射 (columns) =======================================================
  x       — log2FC（数值）
  y       — p 值（数值）
  label   — 基因名（可选）
  group   — 分组（可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(log2FC), 第2列=y(p值), 第3列=label(基因名,可选), 第4列=facet(分面列,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_label = _df_cols[2] if len(_df_cols) > 2 else None
col_facet = _df_cols[3] if len(_df_cols) > 3 else None
col_group = col_color = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Volcano Plot | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM lfc_threshold: float = 1.0 | log2FC 阈值
# @PARAM p_threshold: float = 0.05 | p 值阈值
# @PARAM color_up: str = #E64B35 | 上调基因颜色
# @PARAM color_down: str = #4DBBD5 | 下调基因颜色
# @PARAM color_ns: str = #AAAAAA | 不显著基因颜色
# @PARAM top_n_labels: int = 8 | 标注前 N 个显著基因

title        = str(params.get('title', 'Volcano Plot'))
x_label      = str(params.get('x_label', 'log2 Fold Change'))
y_label      = str(params.get('y_label', '-log₁₀(p-value)'))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 8))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
lfc_thr      = float(params.get('lfc_threshold', 1.0))
p_thr        = float(params.get('p_threshold', 0.05))
color_up     = str(params.get('color_up', '#E64B35'))
color_down   = str(params.get('color_down', '#4DBBD5'))
color_ns     = str(params.get('color_ns', '#AAAAAA'))
top_n_labels = int(params.get('top_n_labels', 8))

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

if not has_x:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break

if not has_y:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) and c != col_x:
            col_y = c
            has_y = True
            break

has_label = col_label and col_label in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    df = df.copy()
    df['_neglog'] = -np.log10(df[col_y].replace(0, 1e-300))

    up = (df[col_x] >= lfc_thr) & (df[col_y] < p_thr)
    dn = (df[col_x] <= -lfc_thr) & (df[col_y] < p_thr)
    ns = ~(up | dn)

    ax.scatter(df.loc[ns, col_x], df.loc[ns, '_neglog'],
               s=55, c=color_ns, alpha=0.5, edgecolors='none')
    ax.scatter(df.loc[dn, col_x], df.loc[dn, '_neglog'],
               s=55, c=color_down, alpha=0.75,
               edgecolors='white', linewidth=0.3)
    ax.scatter(df.loc[up, col_x], df.loc[up, '_neglog'],
               s=55, c=color_up, alpha=0.75,
               edgecolors='white', linewidth=0.3)

    # 阈值线
    ax.axhline(-np.log10(p_thr), color='grey',
               linestyle='--', linewidth=0.8)
    ax.axvline(lfc_thr, color='grey', linestyle='--', linewidth=0.8)
    ax.axvline(-lfc_thr, color='grey', linestyle='--', linewidth=0.8)

    # 显著基因标签
    if has_label and up.sum() > 0:
        top_up = df[up].nlargest(min(top_n_labels, up.sum()), col_y)
        for _, row in top_up.iterrows():
            ax.text(row[col_x], row['_neglog'], str(row[col_label]),
                    fontsize=font_size - 4, ha='left', va='bottom')

    ax.set_xlabel(x_label, fontsize=font_size)
    ax.set_ylabel(y_label, fontsize=font_size)

    # 图例
    legend_elements = [
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor=color_up,
               label=f'Up ({up.sum()})'),
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor=color_down,
               label=f'Down ({dn.sum()})'),
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor=color_ns,
               label=f'NS ({ns.sum()})'),
    ]
    ax.legend(handles=legend_elements, fontsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    msg = '请上传数据并配置列映射\n(columns → x, y)'
    ax.text(0.5, 0.5, msg, ha='center', va='center',
            fontsize=14, color='#999', transform=ax.transAxes)

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
