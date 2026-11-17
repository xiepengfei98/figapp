#!/usr/bin/env python3
"""
和弦图 (Chord Diagram) — Python 版本
=====================================

【图表涵义】
和弦图展示节点之间的流动或连接关系，节点沿圆环排列，
连接弧线的粗细表示关系强度，用于可视化网络流或转移关系。

【适用场景】
- 基因在通路之间的交叉映射
- 细胞类型之间的分化关系
- 物种/样本之间的共享或转移关系

【数据要求】
- x: 来源节点（分类）
- y: 目标节点（分类）
- label: 连接值/权重（数值）

=== 列名映射 (columns) =======================================================
  x       — 来源节点
  y       — 目标节点
  label   — 连接值/权重（数值）
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
# 4. 列名映射 — 按列顺序: 第1列=x(来源节点), 第2列=y(目标节点), 第3列=label(连接值), 第4列=facet(可选)
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
# @PARAM fig_width: float = 8 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 10 | 基础字号
# @PARAM node_size: float = 200 | 节点大小
# @PARAM alpha: float = 0.3 | 连接弧透明度
# @PARAM max_ribbon_width: float = 0.5 | 最大连接带宽度

title            = str(params.get('title', ''))
fig_width        = float(params.get('fig_width', 8))
fig_height       = float(params.get('fig_height', 8))
dpi              = int(params.get('dpi', 300))
font_size        = int(params.get('font_size', 10))
node_size        = float(params.get('node_size', 200))
alpha            = float(params.get('alpha', 0.3))
max_ribbon_width = float(params.get('max_ribbon_width', 0.5))

sns.set_style('whitegrid')
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

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.set_aspect('equal')
ax.axis('off')

if has_x and has_y and has_label:
    # 汇总连接值
    plot_df = df.groupby([col_x, col_y], as_index=False)[col_label].sum()

    # 获取所有唯一节点（保持顺序）
    all_nodes = list(dict.fromkeys(
        pd.concat([plot_df[col_x], plot_df[col_y]])
    ))
    n_nodes = len(all_nodes)
    node_indices = {name: i for i, name in enumerate(all_nodes)}

    # 角度位置
    angles = np.linspace(0, 2 * np.pi, n_nodes, endpoint=False)
    radius = 1.3

    # 绘制节点
    for i, name in enumerate(all_nodes):
        angle = angles[i]
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        color = palette[i % len(palette)]
        ax.scatter(x, y, s=node_size, color=color, zorder=5)
        ax.text(x * 1.15, y * 1.15, str(name),
                ha='center', va='center', fontsize=font_size - 2)

    # 绘制连接带
    max_val = plot_df[col_label].max() if has_label else 1

    for _, row in plot_df.iterrows():
        i1 = node_indices[row[col_x]]
        i2 = node_indices[row[col_y]]
        a1 = angles[i1]
        a2 = angles[i2]

        # 确保弧线走较短路径
        if abs(a1 - a2) > np.pi:
            a1, a2 = a2, a1

        ribbon_w = (row[col_label] / max_val) * max_ribbon_width

        # 计算弧线上的点
        n_pts = 50
        t = np.linspace(0, 1, n_pts)
        arc_angles = a1 + (a2 - a1) * t
        cx_pts = radius * np.cos(arc_angles)
        cy_pts = radius * np.sin(arc_angles)

        # 径向偏移
        mx = np.mean(cx_pts)
        my = np.mean(cy_pts)
        norm = np.sqrt(mx**2 + my**2)
        if norm > 0:
            mx /= norm
            my /= norm

        offset = ribbon_w * np.sin(np.pi * t)
        x_pts = cx_pts + mx * offset
        y_pts = cy_pts + my * offset

        color = palette[i1 % len(palette)]
        ax.fill_between(x_pts, y_pts, 0,
                        alpha=alpha, color=color, zorder=2)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 4, fontweight='bold', pad=20)

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
