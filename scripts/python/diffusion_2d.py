#!/usr/bin/env python3
"""
2D 扩散映射图 (2D Diffusion Map) — Python 版本
=================================================

【图表涵义】
2D 扩散映射图是一种非线性降维方法，通过扩散距离保留数据的局部和全局结构，
展示高维数据的低维嵌入，适合复杂流形结构的数据。

【适用场景】
- 高维数据的非线性降维可视化
- 单细胞 RNA-seq 数据的降维展示
- 复杂流形结构的探索

【数据要求】
包含分组列和多个 Gene_* 数值列，自动进行扩散映射计算。
- group: 分组变量（分类）
- 以 Gene_ 开头的列自动为特征列

=== 列名映射 (columns) =======================================================
  group   — 分组变量（分类）
  以 Gene_ 开头的列自动为特征列
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
from scipy.spatial.distance import cdist


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
# 4. 列名映射 — 按列顺序: 第1列=group(分组), 其余为 Gene_* 特征列
# ====================================================================

_df_cols = df.columns.tolist()
col_group = _df_cols[0] if len(_df_cols) > 0 else None
col_x = col_y = col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = 2D Diffusion Map | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.85 | 点透明度
# @PARAM sigma_percentile: float = 15 | 核宽度百分位

title            = str(params.get('title', ''))
fig_width        = float(params.get('fig_width', 10))
fig_height       = float(params.get('fig_height', 7))
dpi              = int(params.get('dpi', 300))
font_size        = int(params.get('font_size', 12))
alpha            = float(params.get('alpha', 0.85))
sigma_percentile = float(params.get('sigma_percentile', 15))

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

# --- 自动选择特征列 ---
has_group = col_group and col_group in df.columns

gene_cols = [c for c in df.columns
             if c.startswith('Gene_') and pd.api.types.is_numeric_dtype(df[c])]
if not gene_cols:
    gene_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and c not in (col_group, col_facet)
    ][:20]

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))
ax.set_facecolor('#ffffff')

if len(gene_cols) >= 3:
    X = df[gene_cols].values
    X_scaled = (X - X.mean(axis=0)) / X.std(axis=0)

    # 扩散映射计算
    D = cdist(X_scaled, X_scaled, metric='euclidean')
    nonzero_D = D[D > 0]
    sigma = np.percentile(nonzero_D, sigma_percentile) if len(nonzero_D) > 0 else np.median(D[D > 0])
    W = np.exp(-D ** 2 / (2 * sigma ** 2))

    D_rowsum = W.sum(axis=1)
    D_sqrt_inv = np.diag(1.0 / np.sqrt(D_rowsum))
    A = D_sqrt_inv @ W @ D_sqrt_inv

    eigenvalues, eigenvectors = np.linalg.eigh(A)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    dc1 = eigenvectors[:, 1]
    dc2 = eigenvectors[:, 2]

    if has_group:
        for i, grp in enumerate(df[col_group].unique()):
            mask = df[col_group] == grp
            ax.scatter(dc1[mask], dc2[mask], s=50, c=palette[i % len(palette)],
                       edgecolors='#333333', linewidth=0.5, alpha=alpha, label=str(grp))
        ax.legend(fontsize=font_size - 1, loc='upper right')
    else:
        ax.scatter(dc1, dc2, s=50, c=palette[0],
                   edgecolors='#333333', linewidth=0.5, alpha=alpha)

    ax.set_xlabel(f'DC1 ({eigenvalues[1]:.3f})', fontsize=font_size)
    ax.set_ylabel(f'DC2 ({eigenvalues[2]:.3f})', fontsize=font_size)
    ax.tick_params(axis='both', labelsize=font_size - 1)
    ax.axhline(0, color='#cccccc', linewidth=0.5)
    ax.axvline(0, color='#cccccc', linewidth=0.5)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold')

else:
    ax.text(0.5, 0.5, '需要至少 3 个 Gene_ 特征列进行扩散映射',
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
