#!/usr/bin/env python3
"""
简单可变相关热图 (Variable Correlation Heatmap) — Python 版本
==============================================================

【图表涵义】
可变相关热图以矩阵形式展示变量间相关系数，单元格颜色反映相关方向和强度，
叠加圆圈大小表示相关绝对值，同时标注数值。

【适用场景】
- 展示变量间相关系数矩阵
- 需要同时展示相关方向和幅度的场景
- 替代传统相关图，增加视觉层次

【数据要求】
长格式数据，每行记录一对变量的相关系数。
- x: 变量1（分类）
- y: 变量2（分类）
- size: 相关系数（数值，-1 到 1）

=== 列名映射 (columns) =======================================================
  x       — 变量1（分类）
  y       — 变量2（分类）
  size    — 相关系数（数值）
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
from matplotlib.colors import LinearSegmentedColormap
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
# 4. 列名映射 — 按列顺序: 第1列=x(变量1), 第2列=y(变量2), 第3列=size(相关系数), 第4列=facet(分面列,可选)
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
has_var1 = col_x and col_x in df.columns
has_var2 = col_y and col_y in df.columns
has_corr = col_size and col_size in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_var1 and has_var2 and has_corr:
    # 透视构建相关矩阵
    all_vars = sorted(set(df[col_x].tolist() + df[col_y].tolist()))
    n_vars = len(all_vars)
    mat = pd.DataFrame(np.eye(n_vars), index=all_vars, columns=all_vars)

    for _, row in df.iterrows():
        v1, v2, corr = row[col_x], row[col_y], row[col_size]
        if v1 in mat.index and v2 in mat.columns:
            mat.loc[v1, v2] = corr
            mat.loc[v2, v1] = corr

    mat = mat.loc[all_vars, all_vars]

    # 自定义色图
    cmap = LinearSegmentedColormap.from_list(
        'custom_rdbu',
        [palette[3] if len(palette) > 3 else '#2166ac',
         '#f7f7f7',
         palette[0]],
        N=256)

    im = ax.imshow(mat.values, cmap=cmap, vmin=-1, vmax=1, aspect='auto')

    # 圆圈表示相关绝对值
    for i in range(n_vars):
        for j in range(n_vars):
            corr_val = mat.iloc[i, j]
            if i != j:
                circle_size = abs(corr_val) * 120
                ax.scatter(j, i, s=circle_size, color='#333333',
                          alpha=0.35, edgecolors='none', zorder=5)
            else:
                ax.scatter(j, i, s=120, color='white',
                          edgecolors='#666666', linewidth=1, zorder=5)

    # 数值标注
    for i in range(n_vars):
        for j in range(n_vars):
            corr_val = mat.iloc[i, j]
            text_color = '#ffffff' if abs(corr_val) > 0.6 else '#222222'
            ax.text(j, i, f'{corr_val:.2f}', ha='center', va='center',
                    fontsize=font_size - 4, color=text_color, zorder=6)

    ax.set_xticks(range(n_vars))
    ax.set_xticklabels(all_vars, rotation=45, ha='right', fontsize=font_size - 1)
    ax.set_yticks(range(n_vars))
    ax.set_yticklabels(all_vars, fontsize=font_size - 1)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=15)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, label='Correlation')
    cbar.ax.tick_params(labelsize=font_size - 1)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5,
            '请上传数据并配置列映射\n(columns → x=var1, y=var2, size=correlation)',
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
