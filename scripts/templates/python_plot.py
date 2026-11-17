#!/usr/bin/env python3
"""
[图表名称] — Python 版本
=========================
[简要描述图表用途]

=== 使用说明 =================================================================
1. 复制此文件到 scripts/python/，重命名为你的脚本名
2. 在 >>> PLOT CODE >>> 和 <<< PLOT CODE <<< 之间编写绘图代码
3. 修改脚本顶部的 @PARAM 声明（可选），定义可调参数
4. 在 scripts.json 中注册新脚本

=== 数据流 ===================================================================
app.py 在运行目录生成 config.json，包含数据路径、参数、列映射、颜色等。
脚本接收 config.json 路径作为唯一命令行参数，自动完成：
  1. 读取配置
  2. 加载全局颜色与字体
  3. 读取数据（自动检测编码）
  4. 提取参数
  5. 保存 PNG + PDF

=== 可用变量（模板已自动解析，可直接在 PLOT CODE 中使用）=====================
  df, col_x, col_y, col_group, col_color, col_facet, col_label, col_size
  palette, title, x_label, y_label
  fig_width(=10), fig_height(=8), dpi(=300), font_size, alpha
"""

import sys
import json
from pathlib import Path

import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


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
# 4. 列名映射 — 按列顺序: 第1列=x, 第2列=y, 第3列=group(可选), ...
#     对于新脚本，请根据实际需要增加或调整列顺序
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分）
# 如需添加可调参数，在下方用 @PARAM 声明：
#   # @PARAM 参数名: 类型 = 默认值 | 显示标签
# 支持类型: str, int, float, bool, select
#   select 类型默认值格式: "选项1|选项2|选项3" 并用 default=选项1
#   实际默认值写前面的值，尾部竖线后的为选项列表
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.7 | 透明度

title      = str(params.get('title', ''))
x_label    = str(params.get('x_label', col_x or ''))
y_label    = str(params.get('y_label', col_y or ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 8))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
alpha      = float(params.get('alpha', 0.7))


# ====================================================================
# >>> PLOT CODE >>> — 在此处编写您的绘图代码
#     可用变量: df, col_x, col_y, col_group, col_color, col_facet,
#               col_label, col_size, palette, title, x_label, y_label,
#               fig_width, fig_height, dpi, font_size, alpha
#
#     请输出 plt 图形到当前 figure，无需调用 savefig/close
# ====================================================================

fig, ax = plt.subplots(figsize=(fig_width, fig_height))

# ==================== 在此开始编写 ====================

# 示例：散点图
if col_x and col_y and col_x in df.columns and col_y in df.columns:
    if col_group and col_group in df.columns:
        for i, (name, grp) in enumerate(df.groupby(col_group)):
            color = palette[i % len(palette)]
            ax.scatter(grp[col_x], grp[col_y], label=str(name),
                       color=color, alpha=alpha, edgecolors='white', linewidth=0.5, s=40)
        ax.legend(fontsize=font_size - 1)
    else:
        ax.scatter(df[col_x], df[col_y], color=palette[0],
                   alpha=alpha, edgecolors='white', linewidth=0.5, s=40)
    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)
else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x, y)',
            ha='center', va='center', fontsize=14, color='#999',
            transform=ax.transAxes)

if title:
    ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

# ==================== 在此结束编写 ====================

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
