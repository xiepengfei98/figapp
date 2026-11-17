#!/usr/bin/env python3
"""
KEGG 通路图 (KEGG Pathway Network) — Python 版本
==================================================

【图表涵义】
KEGG 通路图以网络图形式展示 KEGG 通路中基因或化合物之间的调控关系，
节点代表基因或化合物，箭头表示激活或抑制关系。

【适用场景】
- KEGG 通路中基因调控关系的可视化
- 信号转导通路的网络展示
- 基因-基因交互关系图

【数据要求】
- x: 源节点（分类）
- y: 目标节点（分类）
- group: 边类型（可选，如激活/抑制）

=== 列名映射 (columns) =======================================================
  x       — 源节点名称（分类）
  y       — 目标节点名称（分类）
  group   — 边类型（可选，如 activation/inhibition）
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
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
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
# 4. 列名映射 — 按列顺序: 第1列=x(源节点), 第2列=y(目标节点), 第3列=group(边类型)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 14 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM node_color: str = #4DBBD5 | 节点颜色
# @PARAM node_size: int = 2000 | 节点大小

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 14))
fig_height = float(params.get('fig_height', 8))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
node_color = str(params.get('node_color', '#4DBBD5'))
node_size  = int(params.get('node_size', 2000))

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
has_group = col_group and col_group in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.axis('off')

if has_x and has_y:
    try:
        import networkx as nx

        G = nx.DiGraph()
        for _, row in df.iterrows():
            G.add_edge(str(row[col_x]), str(row[col_y]))

        pos = nx.spring_layout(G, seed=42, k=1.5)

        # 节点
        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_size,
                               node_color=node_color,
                               edgecolors='white', linewidths=2)

        # 标签
        nx.draw_networkx_labels(G, pos, ax=ax,
                                font_size=font_size - 2,
                                font_weight='bold')

        # 边
        for _, row in df.iterrows():
            src = str(row[col_x])
            tgt = str(row[col_y])
            if src in pos and tgt in pos:
                if has_group:
                    edge_type = str(row[col_group]).lower()
                    if 'inhibit' in edge_type:
                        edge_color = '#E64B35'
                    else:
                        edge_color = '#00A087'
                else:
                    edge_color = '#00A087'

                nx.draw_networkx_edges(G, pos,
                                       edgelist=[(src, tgt)],
                                       ax=ax, edge_color=edge_color,
                                       width=2, arrowsize=20,
                                       arrowstyle='-|>',
                                       connectionstyle='arc3,rad=0.1')

        if title:
            ax.set_title(title, fontsize=font_size + 2,
                         fontweight='bold', pad=12)

    except ImportError:
        ax.text(0.5, 0.5, '需要 networkx 库\n请运行: pip install networkx',
                ha='center', va='center', fontsize=14,
                transform=ax.transAxes)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    msg = '请上传数据并配置列映射\n(columns → x, y)'
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
