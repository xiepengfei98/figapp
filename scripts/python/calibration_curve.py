#!/usr/bin/env python3
"""
校准曲线 (Calibration Curve) — Python 版本
===========================================

【图表涵义】
校准曲线（Calibration Curve）评估预测概率与实际观测概率之间的一致性。
完美校准的模型曲线应沿对角线分布，偏离对角线表示预测偏差。

【适用场景】
- 评估分类模型的概率预测准确性
- 比较多个模型的校准程度
- 生物医学中的风险预测模型评估

【数据要求】
- x: 预测概率值（0~1，数值）
- y: 观测频率/实际概率（0~1，数值）
- group: 模型名称（可选，用于多模型比较）

=== 列名映射 (columns) =======================================================
  x       — 预测概率（数值）
  y       — 观测概率（数值）
  group   — 模型名称（可选，用于多模型比较）
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
# 4. 列名映射 — 按列顺序: 第1列=x(预测概率), 第2列=y(观测概率), 第3列=group(模型名称,可选), 第4列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_facet = _df_cols[3] if len(_df_cols) > 3 else None
col_color = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 8 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM equal_aspect: bool = true | 保持等宽高比
# @PARAM show_ideal: bool = true | 显示理想对角线
# @PARAM marker_style: select = o- | 标记样式 [o-, s-, ^-, D-]

title          = str(params.get('title', ''))
x_label        = str(params.get('x_label', ''))
y_label        = str(params.get('y_label', ''))
fig_width      = float(params.get('fig_width', 8))
fig_height     = float(params.get('fig_height', 8))
dpi            = int(params.get('dpi', 300))
font_size      = int(params.get('font_size', 12))
equal_aspect   = str(params.get('equal_aspect', 'true')).lower() == 'true'
show_ideal     = str(params.get('show_ideal', 'true')).lower() == 'true'
marker_style   = str(params.get('marker_style', 'o-'))

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

if not has_x or not has_y:
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not has_x and len(num_cols) >= 1:
        col_x = num_cols[0]
        has_x = True
    if not has_y and len(num_cols) >= 2:
        col_y = num_cols[1]
        has_y = True

has_group = col_group and col_group in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    # 理想对角线
    if show_ideal:
        ax.plot([0, 1], [0, 1], '--', color='grey', linewidth=1,
                label='Ideal', zorder=1)

    if has_group:
        for i, (g, gdf) in enumerate(df.groupby(col_group)):
            gdf = gdf.sort_values(col_x)
            ax.plot(gdf[col_x], gdf[col_y], marker_style,
                    linewidth=1.5, color=palette[i % len(palette)],
                    label=str(g), zorder=3)
    else:
        plot_df = df.sort_values(col_x)
        ax.plot(plot_df[col_x], plot_df[col_y], marker_style,
                linewidth=1.5, color=palette[0], zorder=3)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    if equal_aspect:
        ax.set_aspect('equal')

    ax.set_xlabel(x_label or 'Predicted Probability', fontsize=font_size)
    ax.set_ylabel(y_label or 'Observed Probability', fontsize=font_size)

    ax.legend(fontsize=font_size - 1)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面提示
    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x, y)',
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
