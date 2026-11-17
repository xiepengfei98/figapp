#!/usr/bin/env python3
"""
相关图 (Correlogram) — Python 版本
===================================

【图表涵义】
相关图展示多个变量之间的相关系数矩阵，通过颜色渐变和数值标注反映变量间的
相关方向和强度，是探索性数据分析和多变量关系研究的常用工具。

【适用场景】
- 展示多变量之间的相关关系矩阵
- 基因表达或指标之间的相关性分析
- 探索性数据分析和变量筛选

【数据要求】
数据为相关系数矩阵（宽格式）：
- x: 变量名列（分类），作为行列标签
- 其余列为数值型相关系数矩阵

=== 列名映射 (columns) =======================================================
  x       — 变量名列，作为行列标签
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
# 4. 列名映射 — 按列顺序: 第1列=x(变量名列), 第2列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_facet = _df_cols[1] if len(_df_cols) > 1 else None
col_y = col_group = col_color = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 9 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM cmap: str = RdBu_r | 颜色映射 [RdBu_r,coolwarm,viridis,YlOrRd]
# @PARAM show_values: bool = true | 显示相关系数值
# @PARAM show_half: bool = true | 仅显示三角区域
# @PARAM half_type: select = lower | 三角形 [lower,upper]

title       = str(params.get('title', ''))
fig_width   = float(params.get('fig_width', 9))
fig_height  = float(params.get('fig_height', 7))
dpi         = int(params.get('dpi', 300))
font_size   = int(params.get('font_size', 12))
cmap        = str(params.get('cmap', 'RdBu_r'))
show_values = str(params.get('show_values', 'true')).lower() == 'true'
show_half   = str(params.get('show_half', 'true')).lower() == 'true'
half_type   = str(params.get('half_type', 'lower'))

sns.set_style('white')
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

if not has_x:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break

# --- 准备相关系数矩阵 ---
if has_x:
    corr_mat = df.set_index(col_x).astype(float)
else:
    corr_mat = df.select_dtypes(include=[np.number]).corr()

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if corr_mat.empty or corr_mat.shape[0] < 2:
    ax.text(0.5, 0.5, '请上传数据并配置列映射\n(columns → x)',
            ha='center', va='center', fontsize=14, color='#999',
            transform=ax.transAxes)
else:
    # 三角遮罩
    mask = None
    if show_half:
        mask = np.zeros_like(corr_mat, dtype=bool)
        if half_type == 'upper':
            mask[np.tril_indices_from(mask)] = True
        else:
            mask[np.triu_indices_from(mask)] = True

    annot = None
    if show_values:
        annot = corr_mat.map(lambda x: f'{x:.2f}' if pd.notna(x) else '')

    sns.heatmap(corr_mat, annot=annot, fmt='', cmap=cmap,
                vmin=-1, vmax=1, center=0,
                mask=mask, square=True, linewidths=1, linecolor='white',
                cbar_kws={'shrink': 0.8},
                annot_kws={'fontsize': font_size - 1},
                xticklabels=True, yticklabels=True, ax=ax)

    # 标签
    ax.tick_params(axis='x', rotation=45, labelsize=font_size - 2)
    ax.tick_params(axis='y', rotation=0, labelsize=font_size - 2)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

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
