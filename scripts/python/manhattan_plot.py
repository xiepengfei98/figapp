#!/usr/bin/env python3
"""
曼哈顿图 (Manhattan Plot) — Python 版本
=========================================

【图表涵义】
曼哈顿图以 -log10(p-value) 在染色体上的位置展示全基因组关联分析结果，
每条染色体用不同颜色区分，显著性阈值线标记显著 SNP。

【适用场景】
- GWAS 分析结果展示
- 全基因组关联信号的定位可视化
- SNP 与表型关联的显著性展示

【数据要求】
- x: 染色体编号（分类）
- y: p 值（数值）
- label: SNP 名称（可选）
- size: BP 位置（数值）

=== 列名映射 (columns) =======================================================
  x       — 染色体编号（分类）
  y       — p 值（数值，自动取 -log10）
  label   — SNP 名称（可选）
  size    — BP 位置（可选，影响点排序）
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
# 4. 列名映射 — 按列顺序: 第1列=x(染色体编号), 第2列=y(p值), 第3列=size(BP位置,可选), 第4列=label(SNP名称,可选), 第5列=facet(分面,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_size = _df_cols[2] if len(_df_cols) > 2 else None
col_label = _df_cols[3] if len(_df_cols) > 3 else None
col_facet = _df_cols[4] if len(_df_cols) > 4 else None
col_color = col_group = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Manhattan Plot | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 5 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM genomewide: float = 5e-8 | 基因组显著性阈值
# @PARAM suggestive: float = 1e-5 | 建议性阈值

title       = str(params.get('title', 'Manhattan Plot'))
x_label     = str(params.get('x_label', 'Chromosome'))
y_label     = str(params.get('y_label', '-log₁₀(p-value)'))
fig_width   = float(params.get('fig_width', 12))
fig_height  = float(params.get('fig_height', 5))
dpi         = int(params.get('dpi', 300))
font_size   = int(params.get('font_size', 12))
genomewide  = float(params.get('genomewide', 5e-8))
suggestive  = float(params.get('suggestive', 1e-5))

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
has_bp = col_size and col_size in df.columns

if not has_y:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    # 计算 -log10(p)
    df = df.copy()
    df['_logp'] = -np.log10(df[col_y].replace(0, 1e-300))

    # 排序
    if has_bp:
        df = df.sort_values([col_x, col_size])
    else:
        df = df.sort_values(col_x)

    # 染色体颜色交替
    df[col_x] = df[col_x].astype(str)
    chromosomes = df[col_x].unique()
    chr_colors = [palette[0], palette[1]]
    alt_colors = [chr_colors[i % 2] for i in range(len(chromosomes))]

    for i, chr_name in enumerate(chromosomes):
        sub = df[df[col_x] == chr_name]
        ax.scatter(sub.index, sub['_logp'], s=6,
                   c=alt_colors[i], alpha=0.7, linewidth=0)

    # 阈值线
    ax.axhline(-np.log10(genomewide), color='red', linestyle='--',
               linewidth=0.8, label=f'p={genomewide:.0e}')
    ax.axhline(-np.log10(suggestive), color='blue', linestyle=':',
               linewidth=0.6, label=f'p={suggestive:.0e}')

    # X 轴标签（染色体名居中）
    chr_mid = [df[df[col_x] == c].index.mean() for c in chromosomes]
    ax.set_xticks(chr_mid)
    ax.set_xticklabels(chromosomes, fontsize=font_size - 4)
    ax.set_xlabel(x_label, fontsize=font_size)
    ax.set_ylabel(y_label, fontsize=font_size)
    ax.legend(fontsize=font_size - 2)

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
