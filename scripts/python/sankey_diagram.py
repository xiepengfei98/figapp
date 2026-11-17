#!/usr/bin/env python3
"""
桑基图 (Sankey Diagram) — Python 版本
========================================

【图表涵义】
桑基图展示节点间的流量或能量流动，流线宽度表示流量大小，
节点左右排列，流线从左向右。

【适用场景】
- 基因通路间的流量分配
- 细胞分化路径的展示
- 样本分组转移的可视化

【数据要求】
- x: 源节点（分类）
- y: 目标节点（分类）
- label: 流量值（数值）

=== 列名映射 (columns) =======================================================
  x       — 源节点（分类）
  y       — 目标节点（分类）
  label   — 流量值（数值）
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
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM color_src: str = E64B35 | 源节点颜色
# @PARAM color_tgt: str = 4DBBD5 | 目标节点颜色

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 6))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
color_src  = str(params.get('color_src', '#E64B35'))
color_tgt  = str(params.get('color_tgt', '#4DBBD5'))

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
    # 节点布局
    src_nodes = df[col_x].unique()
    tgt_nodes = df[col_y].unique()
    all_nodes = list(dict.fromkeys(list(src_nodes) + list(tgt_nodes)))

    split = len(src_nodes)
    left_nodes = all_nodes[:split]
    right_nodes = all_nodes[split:]

    # 节点垂向位置
    n_left = len(left_nodes)
    n_right = len(right_nodes)

    def y_positions(nodes, total):
        return {n: (i + 1) / (total + 1) for i, n in enumerate(nodes)}

    left_pos = y_positions(left_nodes, n_left)
    right_pos = y_positions(right_nodes, n_right)

    # 绘制流线
    for _, row in df.iterrows():
        src = row[col_x]
        tgt = row[col_y]
        if src in left_pos and tgt in right_pos:
            y0 = left_pos[src]
            y1 = right_pos[tgt]
            lw = np.log(row[col_label] + 1) * 2
            ax.plot([0, 0.4, 0.6, 1], [y0, y0, y1, y1],
                    color='#888888', alpha=0.4, linewidth=min(lw, 8))

    # 左边节点
    for n in left_nodes:
        y = left_pos[n]
        ax.scatter(0, y, s=200, color=color_src,
                   zorder=5, edgecolors='white', linewidth=0.5)
        ax.text(-0.1, y, str(n), ha='right', va='center',
                fontsize=font_size - 2)

    # 右边节点
    for n in right_nodes:
        y = right_pos[n]
        ax.scatter(1, y, s=200, color=color_tgt,
                   zorder=5, edgecolors='white', linewidth=0.5)
        ax.text(1.1, y, str(n), ha='left', va='center',
                fontsize=font_size - 2)

    ax.set_xlim(-0.3, 1.3)
    ax.set_ylim(-0.1, 1.1)

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
