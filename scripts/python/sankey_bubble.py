#!/usr/bin/env python3
"""
组合桑基气泡图 (Sankey Bubble Chart) — Python 版本
=====================================================

【图表涵义】
组合桑基气泡图结合桑基流向图与气泡图，展示节点间流量及节点总流量大小，
气泡表示节点，流线表示流向和流量。

【适用场景】
- 基因调控网络中的交互强度可视化
- 分类间的样本流动展示
- 流程中的流量分配可视化

【数据要求】
- x: 源节点（分类）
- y: 目标节点（分类）
- label: 流量值（数值）

=== 列名映射 (columns) =======================================================
  x       — 源节点（分类）
  y       — 目标节点（分类）
  label   — 流量值（数值）
  size    — 节点大小（数值，可选）
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
import matplotlib.patches as mpatches
from matplotlib.path import Path
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
# 4. 列名映射 — 按列顺序: 第1列=x(源节点), 第2列=y(目标节点), 第3列=label(流量值)
# ====================================================================
_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_label = _df_cols[2] if len(_df_cols) > 2 else None
col_group = col_color = col_facet = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 12 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM color_src: str = E64B35 | 源节点颜色
# @PARAM color_tgt: str = 4DBBD5 | 目标节点颜色
# @PARAM max_line_width: float = 8 | 流线最大宽度

title          = str(params.get('title', ''))
fig_width      = float(params.get('fig_width', 12))
fig_height     = float(params.get('fig_height', 8))
dpi            = int(params.get('dpi', 300))
font_size      = int(params.get('font_size', 12))
color_src      = str(params.get('color_src', '#E64B35'))
color_tgt      = str(params.get('color_tgt', '#4DBBD5'))
max_line_width = float(params.get('max_line_width', 8))

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
ax.axis('off')

if has_x and has_y and has_label:
    # 获取节点
    all_nodes = list(dict.fromkeys(pd.concat([df[col_x], df[col_y]])))
    left_nodes = list(dict.fromkeys(df[col_x]))
    right_nodes = [n for n in all_nodes if n not in left_nodes]

    # 计算节点总流量
    node_flow = {}
    for n in all_nodes:
        out_sum = df[df[col_x] == n][col_label].sum()
        in_sum = df[df[col_y] == n][col_label].sum()
        node_flow[n] = max(out_sum, in_sum)

    max_flow = max(node_flow.values()) if node_flow else 1

    # 节点位置
    n_left = len(left_nodes)
    n_right = len(right_nodes)
    left_y = {n: (i + 1) * fig_height / (n_left + 1) for i, n in enumerate(left_nodes)}
    right_y = {n: (i + 1) * fig_height / (n_right + 1) for i, n in enumerate(right_nodes)}

    # 绘制流向
    for _, row in df.iterrows():
        if row[col_x] in left_y and row[col_y] in right_y:
            y0 = left_y[row[col_x]]
            y1 = right_y[row[col_y]]
            w = np.log(row[col_label] + 1) * 2

            verts = [(0, y0), (0.3, y0), (0.7, y1), (1, y1)]
            codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
            ax.add_patch(mpatches.PathPatch(
                Path(verts, codes), facecolor='none',
                edgecolor='#555555', alpha=0.35,
                linewidth=min(w, max_line_width)))

    # 源节点气泡
    for n, y_pos in left_y.items():
        sz = np.sqrt(node_flow[n] / max_flow) * 40 + 10
        ax.scatter(0, y_pos, s=sz ** 2, color=color_src,
                   alpha=0.8, zorder=5,
                   edgecolors='white', linewidth=0.5)
        ax.text(0, y_pos, str(n), ha='center', va='center',
                fontsize=font_size - 3, fontweight='bold')

    # 目标节点气泡
    for n, y_pos in right_y.items():
        sz = np.sqrt(node_flow[n] / max_flow) * 40 + 10
        ax.scatter(1, y_pos, s=sz ** 2, color=color_tgt,
                   alpha=0.8, zorder=5,
                   edgecolors='white', linewidth=0.5)
        ax.text(1, y_pos, str(n), ha='center', va='center',
                fontsize=font_size - 3, fontweight='bold')

    ax.set_xlim(-0.2, 1.2)
    ax.set_ylim(0, fig_height)

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
