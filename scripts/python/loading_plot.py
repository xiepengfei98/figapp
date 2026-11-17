#!/usr/bin/env python3
"""
载荷图 (Loading Plot / PCA Loadings) — Python 版本
===================================================

【图表涵义】
载荷图展示 PCA 中各变量对主成分的贡献度，用箭头方向和长度表示
变量与主成分的相关性。箭头指向同一方向表示正相关。

【适用场景】
- PCA 分析中变量贡献度的可视化
- 高维数据中特征与主成分关系探索
- 变量间的相关性模式展示

【数据要求】
- x: PC1 载荷值（数值）
- y: PC2 载荷值（数值）
- label: 变量名（分类，可选）

=== 列名映射 (columns) =======================================================
  x       — PC1 载荷值（数值）
  y       — PC2 载荷值（数值）
  label   — 变量名（可选）
  group   — 分组（可选）
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
from matplotlib.lines import Line2D
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
# 4. 列名映射 — 按列顺序: 第1列=x(PC1载荷), 第2列=y(PC2载荷), 第3列=label(变量名,可选), 第4列=group(分组,可选), 第5列=facet(分面,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_label = _df_cols[2] if len(_df_cols) > 2 else None
col_group = _df_cols[3] if len(_df_cols) > 3 else None
col_facet = _df_cols[4] if len(_df_cols) > 4 else None
col_color = col_size = col_subgroup = None


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
# @PARAM add_labels: bool = true | 显示变量标签
# @PARAM show_circle: bool = true | 显示单位圆

title       = str(params.get('title', ''))
x_label     = str(params.get('x_label', col_x or ''))
y_label     = str(params.get('y_label', col_y or ''))
fig_width   = float(params.get('fig_width', 10))
fig_height  = float(params.get('fig_height', 8))
dpi         = int(params.get('dpi', 300))
font_size   = int(params.get('font_size', 12))
add_labels  = str(params.get('add_labels', 'true')).lower() == 'true'
show_circle = str(params.get('show_circle', 'true')).lower() == 'true'

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
has_label_col = col_label and col_label in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    # 单位圆
    if show_circle:
        theta = np.linspace(0, 2 * np.pi, 200)
        ax.plot(np.cos(theta), np.sin(theta), color='#999999',
                linestyle='--', linewidth=0.6)
    ax.axhline(y=0, linestyle='dashed', color='#999999', linewidth=0.6)
    ax.axvline(x=0, linestyle='dashed', color='#999999', linewidth=0.6)

    # 绘制箭头
    if has_group:
        for i, (g, grp) in enumerate(df.groupby(col_group)):
            color = palette[i % len(palette)]
            for _, row in grp.iterrows():
                ax.arrow(0, 0, row[col_x], row[col_y], width=0.005,
                         head_width=0.06, head_length=0.08,
                         fc=color, ec=color, alpha=0.8,
                         length_includes_head=True)
    else:
        for _, row in df.iterrows():
            ax.arrow(0, 0, row[col_x], row[col_y], width=0.005,
                     head_width=0.06, head_length=0.08,
                     fc='#333333', ec='#333333', alpha=0.8,
                     length_includes_head=True)

    # 标签
    if add_labels and has_label_col:
        for _, row in df.iterrows():
            off = 0.05
            ax.text(row[col_x] + off * np.sign(row[col_x]),
                    row[col_y] + off * np.sign(row[col_y]),
                    str(row[col_label]), fontsize=font_size - 2,
                    ha='center', va='center')

    # 图例
    if has_group:
        handles = [
            Line2D([0], [0], color=palette[i % len(palette)],
                   lw=2, label=str(g))
            for i, g in enumerate(df[col_group].unique())
        ]
        ax.legend(handles=handles, fontsize=font_size - 1)

    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)
    ax.set_aspect('equal')

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

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
