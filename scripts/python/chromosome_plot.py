#!/usr/bin/env python3
"""
染色体图 (Chromosome Ideogram) — Python 版本
=============================================

【图表涵义】
染色体图（Chromosome Ideogram）展示基因或标记在染色体上的物理位置，
用矩形条表示染色体上的特征区域，类似基因组浏览器视图。

【适用场景】
- 展示基因、SNP 或其他特征在染色体上的分布
- 基因组区域的可视化定位
- 比较不同染色体上的特征密度

【数据要求】
- x: 染色体编号（分类）
- y: 起始位置（数值，bp）
- label: 终止位置（数值，bp）

=== 列名映射 (columns) =======================================================
  x       — 染色体编号（分类）
  y       — 起始位置（数值，bp）
  label   — 终止位置（数值，bp）
  group   — 额外分组（可选）
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
from matplotlib.patches import Rectangle
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
# 4. 列名映射 — 按列顺序: 第1列=x(染色体编号), 第2列=y(起始位置), 第3列=label(终止位置), 第4列=facet(可选)
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

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM bar_height: float = 0.5 | 特征条高度
# @PARAM alpha: float = 0.75 | 填充透明度

title       = str(params.get('title', ''))
x_label     = str(params.get('x_label', ''))
y_label     = str(params.get('y_label', ''))
fig_width   = float(params.get('fig_width', 12))
fig_height  = float(params.get('fig_height', 8))
dpi         = int(params.get('dpi', 300))
font_size   = int(params.get('font_size', 12))
bar_height  = float(params.get('bar_height', 0.5))
alpha       = float(params.get('alpha', 0.75))

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
has_label = col_label and col_label in df.columns

if not has_x:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break

if not has_y:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) and c != col_x:
            col_y = c
            has_y = True
            break

if not has_label and has_y:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) and c not in (col_x, col_y):
            col_label = c
            has_label = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_label:
    # 按染色体排序
    def chr_sort_key(name):
        """尝试按数字排序染色体"""
        s = str(name).lower().replace('chr', '')
        try:
            return (0, int(s))
        except ValueError:
            return (1, s)

    chromosomes = sorted(df[col_x].unique(), key=chr_sort_key)

    for ci, chr_name in enumerate(chromosomes):
        y_base = ci * 2
        chr_data = df[df[col_x] == chr_name]

        # 染色体骨架
        chr_len = chr_data[col_label].max()
        ax.plot([0, chr_len], [y_base, y_base],
                color='#666666', linewidth=3, zorder=1)

        # 绘制特征
        for _, row in chr_data.iterrows():
            start = row[col_y]
            end = row[col_label]
            color = palette[ci % len(palette)]
            rect = Rectangle((start, y_base - bar_height / 2),
                             end - start, bar_height,
                             facecolor=color, edgecolor='#4d4d4d',
                             linewidth=0.5, alpha=alpha)
            ax.add_patch(rect)

        # 染色体标签
        ax.text(-chr_len * 0.02, y_base, str(chr_name),
                ha='right', va='center', fontsize=font_size - 1)

    ax.set_xlabel(x_label or 'Position (bp)', fontsize=font_size)
    ax.set_ylim(-1, len(chromosomes) * 2)
    ax.set_yticks([])

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面提示
    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    msg = '请上传数据并配置列映射\n(columns → x, y, label)'
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
