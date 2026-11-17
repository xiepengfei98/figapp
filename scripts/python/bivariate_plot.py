#!/usr/bin/env python3
"""
双变量图 (Bivariate Plot) — Python 版本
========================================

【图表涵义】
双变量图通过二维核密度估计（KDE）展示两个连续变量的联合分布，
用等高线或颜色填充表示密度区域，同时叠加散点显示原始数据。

【适用场景】
- 展示两个连续变量的联合分布形态
- 识别双变量数据中的聚集区域和离群点
- 替代散点图，在大样本时更好地展示密度信息

【数据要求】
- x: X 轴数值变量（数值）
- y: Y 轴数值变量（数值）

=== 列名映射 (columns) =======================================================
  x       — X 轴数值变量（数值）
  y       — Y 轴数值变量（数值）
  group   — 分组变量（可选）
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

from scipy.stats import gaussian_kde


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
# 4. 列名映射 — 按列顺序: 第1列=x, 第2列=y
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 8 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM cmap: select = RdYlBu_r | 颜色映射 [RdYlBu_r, viridis, plasma, coolwarm, Blues]
# @PARAM n_levels: int = 15 | 等高线层级数
# @PARAM alpha_contour: float = 0.6 | 等高线填充透明度
# @PARAM point_size: float = 3 | 散点大小
# @PARAM point_alpha: float = 0.3 | 散点透明度
# @PARAM add_colorbar: bool = true | 显示颜色条

title         = str(params.get('title', ''))
x_label       = str(params.get('x_label', col_x or ''))
y_label       = str(params.get('y_label', col_y or ''))
fig_width     = float(params.get('fig_width', 8))
fig_height    = float(params.get('fig_height', 6))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 12))
cmap_name     = str(params.get('cmap', 'RdYlBu_r'))
n_levels      = int(params.get('n_levels', 15))
alpha_contour = float(params.get('alpha_contour', 0.6))
point_size    = float(params.get('point_size', 3))
point_alpha   = float(params.get('point_alpha', 0.3))
add_colorbar  = str(params.get('add_colorbar', 'true')).lower() == 'true'

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

if not has_x or not has_y:
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not has_x and len(num_cols) >= 1:
        col_x = num_cols[0]
        has_x = True
    if not has_y and len(num_cols) >= 2:
        col_y = num_cols[1]
        has_y = True

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    clean_df = df[[col_x, col_y]].dropna()
    x_vals = clean_df[col_x].values
    y_vals = clean_df[col_y].values

    # 二维 KDE
    xi, yi = np.mgrid[x_vals.min():x_vals.max():100j,
                      y_vals.min():y_vals.max():100j]
    kde = gaussian_kde(np.vstack([x_vals, y_vals]))
    zi = kde(np.vstack([xi.flatten(), yi.flatten()])).reshape(xi.shape)

    # 等高线填充
    contour = ax.contourf(xi, yi, zi, levels=n_levels,
                          alpha=alpha_contour, cmap=cmap_name)
    if add_colorbar:
        plt.colorbar(contour, ax=ax, label='Density')

    # 叠加散点
    ax.scatter(x_vals, y_vals, s=point_size,
               alpha=point_alpha, color='black', edgecolors='none')

    # 标签
    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 分面提示
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
