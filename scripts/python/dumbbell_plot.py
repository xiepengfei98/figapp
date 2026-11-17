#!/usr/bin/env python3
"""
哑铃图 (Dumbbell Plot) — Python 版本
======================================

【图表涵义】
哑铃图（Dumbbell Plot）用线段连接两个端点（前后、前后测、前后状态），
展示每个类别在两个时间点或状态下的数值变化。线段长度反映变化幅度。

【适用场景】
- 展示前后测或处理前后的数值变化
- 两组间配对比较的可视化
- 基因表达在治疗前后的变化

【数据要求】
- x: 类别变量（分类）
- y: 时间点2/处理后数值（数值）
- label: 时间点1/处理前数值（数值）

=== 列名映射 (columns) =======================================================
  x       — 类别变量（分类）
  y       — 时间点2/处理后数值（数值）
  label   — 时间点1/处理前数值（数值）
  group   — 分组变量（可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(类别), 第2列=y(终值), 第3列=label(初值), 第4列=facet(可选)
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
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM color_before: str = #2c7bb6 | 初始值颜色
# @PARAM color_after: str = #d7191c | 终值颜色
# @PARAM marker_before: select = o | 初始值标记 [o, s, ^, D]
# @PARAM marker_after: select = D | 终值标记 [D, o, s, ^]

title        = str(params.get('title', ''))
x_label      = str(params.get('x_label', ''))
y_label      = str(params.get('y_label', 'Value'))
fig_width    = float(params.get('fig_width', 10))
fig_height   = float(params.get('fig_height', 7))
dpi          = int(params.get('dpi', 300))
font_size    = int(params.get('font_size', 12))
color_before = str(params.get('color_before', '#2c7bb6'))
color_after  = str(params.get('color_after', '#d7191c'))
marker_before = str(params.get('marker_before', 'o'))
marker_after  = str(params.get('marker_after', 'D'))

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
        if pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break

if not has_label:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) and c != col_y:
            col_label = c
            has_label = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_label:
    y_pos = np.arange(len(df))
    before = df[col_label].values
    after = df[col_y].values

    # 连接线
    ax.hlines(y=y_pos, xmin=before, xmax=after,
              color='#4d4d4d', linewidth=2, alpha=0.6)

    # 前后端点
    ax.scatter(before, y_pos, s=100, color=color_before,
               edgecolors='#333333', linewidths=0.8,
               zorder=5, marker=marker_before, label=col_label)
    ax.scatter(after, y_pos, s=100, color=color_after,
               edgecolors='#333333', linewidths=0.8,
               zorder=5, marker=marker_after, label=col_y)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(df[col_x], fontsize=font_size - 2)
    ax.set_xlabel(y_label, fontsize=font_size)
    if x_label:
        ax.set_ylabel(x_label, fontsize=font_size)

    ax.legend(fontsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

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
