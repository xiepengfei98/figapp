#!/usr/bin/env python3
"""
基因结构图 (Gene Structure Diagram) — Python 版本
===================================================

【图表涵义】
基因结构图绘制基因的结构模型，矩形框表示外显子/CDS/UTR，
线条表示内含子，箭头指示转录方向。

【适用场景】
- 展示基因的外显子-内含子结构
- 比较多个基因的基因组结构差异
- 基因注释和可视化

【数据要求】
- x: 基因名（分类）
- y: 起始位置（数值）
- size: 结束位置（数值）
- label: 特征类型（可选，exon/cds/utr）

=== 列名映射 (columns) =======================================================
  x       — 基因名（分类）
  y       — 起始位置（数值）
  size    — 结束位置（数值）
  label   — 特征类型（可选）
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
import matplotlib.patches as mpatches
from matplotlib.path import Path as MPath
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
# 4. 列名映射 — 按列顺序: 第1列=x(基因名), 第2列=y(起始位置), 第3列=size(结束位置), 第4列=label(特征类型)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_size = _df_cols[2] if len(_df_cols) > 2 else None
col_label = _df_cols[3] if len(_df_cols) > 3 else None
col_group = col_color = col_facet = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 5 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号

title      = str(params.get('title', ''))
x_label    = str(params.get('x_label', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 5))
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
has_x = col_x and col_x in df.columns
has_y = col_y and col_y in df.columns
has_size = col_size and col_size in df.columns
has_label_type = col_label and col_label in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_size:
    genes = sorted(df[col_x].unique())
    n_genes = len(genes)

    for g_idx, gene_name in enumerate(genes):
        y_base = -g_idx * 1.2
        gene_data = df[df[col_x] == gene_name]

        gene_start = gene_data[col_y].min()
        gene_end = gene_data[col_size].max()

        # 内含子线
        ax.plot([gene_start, gene_end], [y_base, y_base],
                '-', color='#999999', linewidth=2, alpha=0.7, zorder=1)

        # 外显子
        for _, row in gene_data.iterrows():
            e_start = row[col_y]
            e_end = row[col_size]
            e_width = e_end - e_start

            if has_label_type:
                e_type = str(row.get(col_label, 'exon')).lower()
                if 'cds' in e_type:
                    e_color = '#00A087'
                elif 'utr' in e_type:
                    e_color = '#F39B7F'
                else:
                    e_color = '#4DBBD5'
            else:
                e_color = '#4DBBD5'

            rect = mpatches.FancyBboxPatch(
                (e_start, y_base - 0.2), e_width, 0.4,
                boxstyle="round,pad=0.02",
                facecolor=e_color, edgecolor='white',
                linewidth=1.5, zorder=3)
            ax.add_patch(rect)

        # 3' 箭头
        arrow_path = MPath([
            (gene_end, y_base),
            (gene_end + 0.3, y_base + 0.18),
            (gene_end + 0.3, y_base - 0.18),
            (gene_end, y_base),
        ], [MPath.MOVETO, MPath.LINETO, MPath.LINETO, MPath.CLOSEPOLY])
        ax.add_patch(mpatches.PathPatch(arrow_path, facecolor='#333333',
                                         edgecolor='none', zorder=2))

        # 标签
        ax.text(gene_start - (gene_end - gene_start) * 0.02, y_base,
                "5'", fontsize=font_size - 3, ha='right',
                va='center', color='#666666')
        ax.text(gene_end + 0.5, y_base,
                "3'", fontsize=font_size - 3, ha='left',
                va='center', color='#666666')
        ax.text(gene_start - (gene_end - gene_start) * 0.08, y_base,
                gene_name, fontsize=font_size - 1, ha='right',
                va='center', fontweight='bold',
                color=palette[g_idx % len(palette)])

    # 图例
    legend_elements = [
        mpatches.Patch(color='#4DBBD5', label='Exon'),
        mpatches.Patch(color='#00A087', label='CDS'),
        mpatches.Patch(color='#F39B7F', label='UTR'),
        mpatches.Patch(color='#999999', label='Intron'),
    ]
    ax.legend(handles=legend_elements, loc='upper right',
              fontsize=font_size - 1, ncol=4, framealpha=0.9)

    ax.set_xlabel(x_label or 'Genomic Position (bp)', fontsize=font_size)
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    msg = '请上传数据并配置列映射\n(columns → x=基因名, y=起始, size=结束)'
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
