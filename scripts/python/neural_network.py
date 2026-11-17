#!/usr/bin/env python3
"""
神经网络图 (Neural Network Architecture) — Python 版本
=======================================================

【图表涵义】
神经网络图可视化多层神经网络的架构，每层节点垂直排列，
层间连线表示连接关系，节点内标注名称。

【适用场景】
- 展示深度学习网络架构
- 可视化多层感知机结构
- 教学和报告中展示网络设计

【数据要求】
- x: 层编号（数值/有序，指定节点所在层）
- y: 节点 ID（分类，每个节点的唯一标识）
- label: 节点标签（分类，显示在节点上的文本）

=== 列名映射 (columns) =======================================================
  x       — 层编号（数值/有序）
  y       — 节点 ID（分类）
  label   — 节点标签（分类）
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
# 4. 列名映射 — 按列顺序: 第1列=x(层编号), 第2列=y(节点ID), 第3列=label(节点标签), 第4列=facet(可选)
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
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM node_size: float = 500 | 节点大小

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 12))
fig_height = float(params.get('fig_height', 8))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
node_size  = float(params.get('node_size', 500))

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
has_layer = col_x and col_x in df.columns
has_node = col_y and col_y in df.columns
has_nlabel = col_label and col_label in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_layer and has_node:
    layers = sorted(df[col_x].unique())
    n_layers = len(layers)

    # 节点位置计算
    node_positions = {}
    layer_node_lists = []

    for i, layer_id in enumerate(layers):
        nodes = df[df[col_x] == layer_id]
        n_nodes = len(nodes)
        y_positions = np.linspace(-(n_nodes - 1) / 2, (n_nodes - 1) / 2, n_nodes)
        node_ids = nodes[col_y].tolist()
        layer_node_lists.append(node_ids)
        for j, (_, row) in enumerate(nodes.iterrows()):
            node_positions[row[col_y]] = (i + 1, y_positions[j])

    # 层间连线
    for layer_idx in range(n_layers - 1):
        src_nodes = layer_node_lists[layer_idx]
        tgt_nodes = layer_node_lists[layer_idx + 1]
        for s in src_nodes:
            x1, y1 = node_positions[s]
            for t in tgt_nodes:
                x2, y2 = node_positions[t]
                ax.plot([x1, x2], [y1, y2], color='#cccccc',
                        linewidth=0.4, alpha=0.6, zorder=1)

    # 节点
    for node_id, (x, y) in node_positions.items():
        layer_idx = int(x) - 1
        color = palette[layer_idx % len(palette)]
        ax.scatter(x, y, s=node_size, color=color,
                   edgecolors='#ffffff', linewidths=1.5, zorder=5)

    # 节点标签
    if has_nlabel:
        for _, row in df.iterrows():
            nid = row[col_y]
            if nid in node_positions:
                x, y = node_positions[nid]
                ax.text(x, y, str(row[col_label]), ha='center', va='center',
                        fontsize=font_size - 5, color='#ffffff',
                        fontweight='bold', zorder=6)
    else:
        for node_id, (x, y) in node_positions.items():
            ax.text(x, y, str(node_id), ha='center', va='center',
                    fontsize=font_size - 5, color='#ffffff',
                    fontweight='bold', zorder=6)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

    ax.set_xlim(0.5, n_layers + 0.5)
    ax.axis('off')

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x=layer, y=node_id, label=text)',
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
