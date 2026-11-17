#!/usr/bin/env python3
"""
UpSet 图 (UpSet Plot) — Python 版本
====================================

【图表涵义】
UpSet 图展示多个集合的交叉组合及其大小，作为韦恩图的替代方案，
能更清晰地展示大量集合间的交集关系。

【适用场景】
- 多个基因集合的交集分析
- 替代韦恩图展示 3 个以上集合的交集
- 展示不同条件/处理下的共有和特有元素

【数据要求】
数据为宽格式二进制矩阵：
- x: 行标识列（如基因名）
- 其余列为数值列，值 1 表示属于该集合，0 表示不属于

=== 列名映射 (columns) =======================================================
  x       — 行标识列（如基因名），作为行标签
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
from itertools import product


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
# 4. 列名映射 — 按列顺序: 第1列=x(行标识列), 其余列为集合列
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_facet = _df_cols[1] if len(_df_cols) > 1 else None
col_y = col_group = col_color = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号

title     = str(params.get('title', ''))
fig_width = float(params.get('fig_width', 10))
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
# ====================================================================

if col_x and col_x in df.columns:
    id_col = col_x
else:
    id_col = df.columns[0]

# 识别集合列（二进制列）
set_cols = [c for c in df.columns if c != id_col]

fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if len(set_cols) >= 2:
    # 计算所有非空交集
    combos_all = []
    for r in range(1, len(set_cols) + 1):
        for combo in product([0, 1], repeat=len(set_cols)):
            if sum(combo) == r:
                combos_all.append(combo)

    counts = []
    for combo in combos_all:
        mask = np.ones(len(df), dtype=bool)
        for j, (c, v) in enumerate(zip(set_cols, combo)):
            if v == 1:
                mask &= (df[c].values == 1)
            else:
                mask &= (df[c].values == 0)
        counts.append(mask.sum())

    combo_df = pd.DataFrame({'count': counts, 'combo': [tuple(c) for c in combos_all]})
    combo_df = combo_df[combo_df['count'] > 0].sort_values('count')
    combo_df = combo_df.reset_index(drop=True)

    # 条形图
    ax.bar(range(len(combo_df)), combo_df['count'],
           color=palette[0], alpha=0.85)
    ax.set_xticks(range(len(combo_df)))
    ax.set_xticklabels([str(c) for c in combo_df['combo']],
                       rotation=45, ha='right', fontsize=font_size - 3)
    ax.set_ylabel("Intersection Size", fontsize=font_size)
    ax.tick_params(labelsize=font_size - 2)
    ax.grid(axis='y', alpha=0.2)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传二进制矩阵数据\n(第一列为标识列，其余为 0/1 集合列)',
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
