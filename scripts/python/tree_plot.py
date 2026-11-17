#!/usr/bin/env python3
"""
树型图 (Hierarchical Tree Plot) — Python 版本
===============================================

【图表涵义】
树型图以递归布局展示层次树结构，根节点位于顶部，子节点向下展开，
节点颜色按深度区分。

【适用场景】
- 展示分类或聚类层次关系
- 组织结构或决策树可视化
- 展示基因家族或系统发育关系

【数据要求】
- x: 父节点列（分类）
- y: 子节点列（分类）

=== 列名映射 (columns) =======================================================
  x       — 父节点（分类）
  y       — 子节点（分类）
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
# 4. 列名映射 — 按列顺序: 第1列=x(父节点), 第2列=y(子节点)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = Hierarchical Tree | 图表标题
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 12))
fig_height = float(params.get('fig_height', 8))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))

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
has_parent = col_x and col_x in df.columns
has_child = col_y and col_y in df.columns

# --- 递归布局函数 ---
def build_layout(df, col_x, col_y, node_name, x=5.0, y=10.0, width=10.0, depth=0):
    children = df[df[col_x] == node_name]
    if len(children) == 0:
        return [{'name': node_name, 'x': x, 'y': y, 'depth': depth}]
    result = [{'name': node_name, 'x': x, 'y': y, 'depth': depth}]
    n_child = len(children)
    child_width = width / n_child
    for i, (_, row) in enumerate(children.iterrows()):
        cx = x - width / 2 + child_width * (i + 0.5)
        cy = y - 1.5
        result.extend(build_layout(df, col_x, col_y, row[col_y], cx, cy,
                                    child_width * 0.8, depth + 1))
    return result

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.set_facecolor('#ffffff')

if has_parent and has_child:
    all_nodes = sorted(set(df[col_x].tolist() + df[col_y].tolist()))
    depth_colors = [palette[i % len(palette)] for i in range(6)]

    root_candidates = [n for n in df[col_x].unique()
                        if n not in df[col_y].values]
    root_node = root_candidates[0] if root_candidates else all_nodes[0]

    layout = build_layout(df, col_x, col_y, root_node)
    layout_df = pd.DataFrame(layout)

    edge_data = []
    for _, row in df.iterrows():
        pr = layout_df[layout_df['name'] == row[col_x]]
        cr = layout_df[layout_df['name'] == row[col_y]]
        if len(pr) > 0 and len(cr) > 0:
            edge_data.append({
                'x': pr.iloc[0]['x'], 'y': pr.iloc[0]['y'],
                'xend': cr.iloc[0]['x'], 'yend': cr.iloc[0]['y']
            })
    edge_df = pd.DataFrame(edge_data) if edge_data else pd.DataFrame()

    layout_df['depth_color'] = [
        depth_colors[d % len(depth_colors)] for d in layout_df['depth']
    ]

    for _, e in edge_df.iterrows():
        ax.plot([e['x'], e['xend']], [e['y'], e['yend']],
                color='#999999', linewidth=1.0, zorder=1)

    for _, node in layout_df.iterrows():
        ax.scatter(node['x'], node['y'], s=200, c=node['depth_color'],
                   edgecolors='#333333', linewidth=1.2, zorder=5)

    for _, node in layout_df.iterrows():
        ax.text(node['x'], node['y'], str(node['name']),
                fontsize=font_size - 5, fontweight='bold', color='#ffffff',
                ha='center', va='center', zorder=6)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    ax.axis('off')

else:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x=parent, y=child)',
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
