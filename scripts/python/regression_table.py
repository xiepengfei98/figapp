#!/usr/bin/env python3
"""
回归分析表格 (Regression Table) — Python 版本
================================================

【图表涵义】
回归分析表格以格式化表格展示回归分析结果，包括变量名、系数、标准误、
p 值等统计量。适用于结果报告的简洁展示。

【适用场景】
- 回归分析结果的表格化呈现
- Cox/LR 回归结果的汇总
- 统计模型的系数表展示

【数据要求】
宽格式数据，第一行为列标题，每行为一个变量。
无需特定列映射，自动使用所有列。

=== 列名映射 ===============================================================
  无需映射，自动使用所有列

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
# 4. 列名映射 — 按列顺序: 无需映射, 自动使用所有列
# ====================================================================
col_x = col_y = col_group = col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = 表格 | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM dpi: int = 150 | 输出分辨率

title     = str(params.get('title', '表格'))
fig_width = float(params.get('fig_width', 10))
dpi       = int(params.get('dpi', 150))

sns.set_style('whitegrid')
sns.set_context('notebook', font_scale=8 / 12)

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

# --- 绘图 ---
fig_height = float(params.get('fig_height', max(2, len(df) * 0.3 + 2)))
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.axis('off')

col_names = list(df.columns)
cell_text = df.values.astype(str)
n_rows = len(df)
n_cols = len(col_names)

# 创建表格
header_color = [0.23, 0.33, 0.53, 1]
cell_color = [0.97, 0.97, 0.97, 1]
cell_colors = np.full((n_rows, n_cols), cell_color)

table = ax.table(cellText=cell_text, colLabels=col_names,
                 cellLoc='center', loc='center',
                 colColours=[header_color] * n_cols,
                 cellColours=cell_colors)

table.auto_set_font_size(False)
table.set_fontsize(9)

for (r, c), cell in table.get_celld().items():
    if r == 0:
        cell.set_text_props(color='white', fontsize=10, fontweight='bold')
    cell.set_edgecolor('#CCCCCC')
    cell.set_linewidth(0.3)

if title:
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

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
