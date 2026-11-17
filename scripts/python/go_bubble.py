#!/usr/bin/env python3
"""
GO 气泡图 (GO Bubble Chart) — Python 版本
===========================================

【图表涵义】
GO 气泡图以气泡形式展示富集分析结果，X 轴为类别，Y 轴为术语名称，
气泡大小表示基因计数，颜色表示富集显著性（p 值）。

【适用场景】
- GO/KEGG 富集结果的多维展示
- 同时展示富集类别、术语、基因数和显著性
- 功能注释的富集气泡图

【数据要求】
- x: GO 类别（分类，如 BP/CC/MF）
- y: GO 术语名称（分类）
- label: 基因计数（数值）
- size: 富集比值（可选）
- color: p 值（数值，可选）

=== 列名映射 (columns) =======================================================
  x       — GO 类别
  y       — GO 术语名称
  label   — 基因计数（数值）
  size    — 富集比值（可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(GO类别), 第2列=y(GO术语), 第3列=label(基因计数), 第4列=color(p值)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_label = _df_cols[2] if len(_df_cols) > 2 else None
col_color = _df_cols[3] if len(_df_cols) > 3 else None
col_group = col_facet = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.8 | 气泡透明度
# @PARAM cmap: str = Reds | 颜色映射
# @PARAM scale_factor: float = 500 | 气泡大小缩放因子

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', 'Category'))
y_label      = str(params.get('y_label', ''))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 8))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
alpha        = float(params.get('alpha', 0.8))
cmap_name    = str(params.get('cmap', 'Reds'))
scale_factor = float(params.get('scale_factor', 500))

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
        if not pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break

if not has_y:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break

has_label = col_label and col_label in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    plot_df = df.copy()

    # 气泡大小
    if has_label:
        sizes = plot_df[col_label] / plot_df[col_label].max() * scale_factor
    else:
        sizes = 100

    # 颜色（使用 group 或 p 值）
    if col_color and col_color in plot_df.columns:
        if pd.api.types.is_numeric_dtype(plot_df[col_color]):
            color_vals = -np.log10(plot_df[col_color].replace(0, 1e-300))
        else:
            color_vals = palette[0]
    else:
        color_vals = palette[0]

    ax.scatter(plot_df[col_x], plot_df[col_y], s=sizes,
               c=color_vals, cmap=cmap_name if isinstance(color_vals, np.ndarray) else None,
               alpha=alpha, edgecolors='grey', linewidth=0.3)

    ax.set_xlabel(x_label, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

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
