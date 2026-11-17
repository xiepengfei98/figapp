#!/usr/bin/env python3
"""
双Y轴图 (Dual Y-Axis Plot) — Python 版本
==========================================

【图表涵义】
双Y轴图在同一图中使用左右两个不同刻度的 Y 轴展示两组不同量纲的数据，
便于比较同一 X 轴下两个变量的变化趋势。

【适用场景】
- 展示两个量纲不同但相关的变量在同一 X 轴下的变化
- 基因表达量与表型指标的关联展示
- 两组不同单位的时间序列数据对比

【数据要求】
- x: X 轴变量（有序/分类）
- y: 左侧 Y 轴变量（数值）
- label: 右侧 Y 轴变量（数值）

=== 列名映射 (columns) =======================================================
  x       — X 轴变量（有序/分类）
  y       — 左侧 Y 轴数值
  label   — 右侧 Y 轴数值
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
# 4. 列名映射 — 按列顺序: 第1列=x, 第2列=y(左轴), 第3列=label(右轴), 第4列=facet(可选)
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
# @PARAM y1_label: str =  | 左侧 Y 轴标签
# @PARAM y2_label: str =  | 右侧 Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM color_left: str = #2c7bb6 | 左侧线条颜色
# @PARAM color_right: str = #d7191c | 右侧线条颜色
# @PARAM marker_left: select = o | 左侧标记 [o, s, ^, D, v]
# @PARAM marker_right: select = s | 右侧标记 [s, o, ^, D, v]

title       = str(params.get('title', ''))
x_label     = str(params.get('x_label', 'X'))
y1_label    = str(params.get('y1_label', 'Y1'))
y2_label    = str(params.get('y2_label', 'Y2'))
fig_width   = float(params.get('fig_width', 10))
fig_height  = float(params.get('fig_height', 6))
dpi         = int(params.get('dpi', 300))
font_size   = int(params.get('font_size', 12))
color_left  = str(params.get('color_left', '#2c7bb6'))
color_right = str(params.get('color_right', '#d7191c'))
marker_left = str(params.get('marker_left', 'o'))
marker_right = str(params.get('marker_right', 's'))

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
    col_x = df.columns[0]
    has_x = True

if not has_y:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break

# --- 绘图 ---
fig, ax1 = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_label:
    x_pos = np.arange(len(df))

    # 左轴
    line1 = ax1.plot(x_pos, df[col_y], color=color_left, linewidth=1.8,
                     marker=marker_left, label=y1_label or col_y)
    ax1.set_xlabel(x_label, fontsize=font_size)
    ax1.set_ylabel(y1_label or col_y, fontsize=font_size, color=color_left)
    ax1.tick_params(axis='y', labelcolor=color_left)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(df[col_x], rotation=45, ha='right', fontsize=font_size - 2)

    # 右轴
    ax2 = ax1.twinx()
    line2 = ax2.plot(x_pos, df[col_label], color=color_right, linewidth=1.8,
                     marker=marker_right, label=y2_label or col_label)
    ax2.set_ylabel(y2_label or col_label, fontsize=font_size, color=color_right)
    ax2.tick_params(axis='y', labelcolor=color_right)

    # 合并图例
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, fontsize=font_size - 1)

    if title:
        ax1.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    msg = '请上传数据并配置列映射\n(columns → x, y, label)'
    ax1.text(0.5, 0.5, msg, ha='center', va='center',
             fontsize=14, color='#999', transform=ax1.transAxes)

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
