#!/usr/bin/env python3
"""
系统树图 (Phylogram / Phylogenetic Tree) — Python 版本
=======================================================

【图表涵义】
系统树图展示生物分类或层次关系的树状结构，节点表示分类单元，
枝长反映进化距离或差异程度。

【适用场景】
- 展示物种进化关系
- 展示层次聚类结果
- 展示基因家族或样本间的系统发育关系

【数据要求】
- x: 父节点列（分类，节点的来源）
- y: 子节点列（分类，节点的去向）
- size: 枝长（数值，可选，反映距离）

=== 列名映射 (columns) =======================================================
  x       — 父节点列（分类）
  y       — 子节点列（分类）
  size    — 枝长（数值，可选）
  facet   — 分面列（可选）

=== @PARAM 说明 ===============================================================
  所有 @PARAM 在右侧面板生成控件，出图后可调参数并重绘。
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
# 4. 列名映射 — 按列顺序: 第1列=x(父节点), 第2列=y(子节点), 第3列=size(枝长,可选), 第4列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_size = _df_cols[2] if len(_df_cols) > 2 else None
col_facet = _df_cols[3] if len(_df_cols) > 3 else None
col_group = col_color = col_label = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 10))
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
has_length = col_size and col_size in df.columns

if not has_parent or not has_child:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            if not has_parent:
                col_x = c
                has_parent = True
            elif not has_child and c != col_x:
                col_y = c
                has_child = True

# --- 树布局函数 ---
def layout_tree(edges, parent_col, child_col, length_col, root):
    """Assign y positions and depths to all nodes."""
    node_y = {}
    current_y = [0]

    def assign_y(node):
        children = edges[edges[parent_col] == node][child_col].tolist()
        if not children:
            node_y[node] = current_y[0]
            current_y[0] += 1
        else:
            for ch in children:
                assign_y(ch)
            child_ys = [node_y[ch] for ch in children]
            node_y[node] = np.mean([min(child_ys), max(child_ys)])

    assign_y(root)

    node_depth = {}
    def calc_depth(node, d=0.0):
        node_depth[node] = d
        for _, row in edges[edges[parent_col] == node].iterrows():
            ch = row[child_col]
            if length_col and length_col in edges.columns:
                calc_depth(ch, d + row[length_col])
            else:
                calc_depth(ch, d + 1)

    calc_depth(root)
    return node_y, node_depth

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.set_facecolor('#ffffff')

if has_parent and has_child:
    edges = df[[col_x, col_y]].copy()
    if has_length:
        edges[col_x + '_len'] = df[col_size]
    else:
        edges[col_x + '_len'] = 1.0

    all_nodes = sorted(set(edges[col_x].tolist() + edges[col_y].tolist()))
    # 找根节点：出现在父列但不出现在子列的节点
    root_candidates = [n for n in edges[col_x].unique()
                       if n not in edges[col_y].values]
    root = root_candidates[0] if root_candidates else all_nodes[0]

    length_col_name = col_x + '_len'
    edges_with_len = edges.rename(columns={col_x: 'from', col_y: 'to',
                                          length_col_name: 'length'})
    node_y, node_depth = layout_tree(
        edges_with_len, 'from', 'to',
        'length' if has_length else None, root)

    for _, row in edges_with_len.iterrows():
        f = row['from']
        t = row['to']
        d_f = node_depth.get(f, 0)
        d_t = node_depth.get(t, 0)
        y_f = node_y.get(f, 0)
        y_t = node_y.get(t, 0)

        ax.plot([d_f, d_t], [y_f, y_t], color='#4d4d4d', linewidth=1.2, zorder=1)
        if y_f != y_t:
            ax.plot([d_f, d_f], [y_f, y_t], color='#4d4d4d', linewidth=1.2, zorder=1)

    for node in all_nodes:
        ax.scatter(node_depth.get(node, 0), node_y.get(node, 0),
                  s=60, color=palette[0], edgecolors='#333333',
                  linewidth=0.5, zorder=5)
        ax.text(node_depth.get(node, 0) + 0.15, node_y.get(node, 0),
                str(node), fontsize=font_size - 2, color='#333333',
                ha='left', va='center')

    ax.set_title(title if title else 'Phylogram',
                 fontsize=font_size + 2, fontweight='bold')
    ax.axis('off')

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

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
