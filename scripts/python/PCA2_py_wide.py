#!/usr/bin/env python3
"""
PCA 图 (Principal Component Analysis Scatter) — Python 版本
============================================================

【图表涵义】
PCA 图展示高维数据降维后的样本分布，PC1 和 PC2 为前两个主成分，
反映样本间的变异方向和组间差异，可添加置信椭圆。

【适用场景】
- 探索高维数据的主要变异方向
- 展示样本分组和聚类结构
- 基因表达数据的降维可视化

【数据要求】
- 输入数据为宽格式矩阵：
  第一行（行索引0）：样本名称
  第二行（行索引1）：分组信息
  其余行（行索引2及之后）：表达量数值，第一列为特征ID（如基因名）
  （若第一列为空，需忽略）

=== 列名映射 (columns) =======================================================
  本版本自动解析宽数据，无需手动映射列名。
  参数 columns 将被忽略。

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
from matplotlib.patches import Ellipse
import seaborn as sns

# MODIFIED: 导入PCA计算模块
from sklearn.decomposition import PCA


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
        return pd.read_excel(filepath, header=None)   # MODIFIED: 无表头读取
    if ext == '.txt':
        return pd.read_csv(filepath, sep='\t', header=None)
    encodings = ['utf-8', 'gbk', 'gb18030', 'latin-1']
    for enc in encodings:
        try:
            return pd.read_csv(filepath, encoding=enc, header=None)
        except (UnicodeDecodeError, TypeError):
            continue
    raise ValueError(f"无法识别文件编码: {filepath}")

df_raw = read_data(input_file)


# ====================================================================
# 4. 数据转换：宽矩阵 → 样本×特征 DataFrame + PCA (MODIFIED)
# ====================================================================

# ---- 提取前两行的元数据 ----
# 第一列可能是特征ID，也可能为空；假定第一列存在
row0 = df_raw.iloc[0, :].tolist()          # 第一行：样本名称
row1 = df_raw.iloc[1, :].tolist()          # 第二行：分组信息
# 第一列的值作为特征名占位，忽略或保留
feature_col_name = row0[0] if pd.notna(row0[0]) else 'FeatureID'
sample_names = [str(x) for x in row0[1:]]     # 样本名称（从第二列开始）
group_labels = [str(x) for x in row1[1:]]     # 分组标签（从第二列开始）

# ---- 提取表达矩阵（特征×样本） ----
# 第三行及之后：第一列为特征ID，其余为表达数值
expr_matrix = df_raw.iloc[2:, :].copy()
feature_ids = expr_matrix.iloc[:, 0].tolist()   # 特征名
# 数值部分（第二列起）转为float
expr_values = expr_matrix.iloc[:, 1:].apply(pd.to_numeric, errors='coerce').values  # 形状: (n_features, n_samples)
# 检查是否有缺失值
if np.any(pd.isna(expr_values)):
    # 简单处理：用列均值填充（可按需修改）
    col_means = np.nanmean(expr_values, axis=0)
    inds = np.where(np.isnan(expr_values))
    expr_values[inds] = np.take(col_means, inds[1])

# 转置为样本×特征矩阵 (n_samples, n_features)
expr_T = expr_values.T    # 形状: (n_samples, n_features)
# 创建DataFrame，行名为样本名，列名为特征ID
df_expr = pd.DataFrame(expr_T, index=sample_names, columns=feature_ids)
# 添加Group列
df_expr['Group'] = group_labels

# ---- PCA降维 ----
pca = PCA(n_components=2)
pcs = pca.fit_transform(df_expr[feature_ids].values)  # 只对数值部分进行PCA
df_expr['PC1'] = pcs[:, 0]
df_expr['PC2'] = pcs[:, 1]

# 替换原始df用于后续绘图
df = df_expr

# 设置绘图所需的列名
col_x = 'PC1'
col_y = 'PC2'
col_group = 'Group'
col_facet = None
col_label = None
col_color = None
col_size = None
col_subgroup = None

# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = PCA 图 | 图表标题
# @PARAM x_label: str = PC1 | X 轴标签
# @PARAM y_label: str = PC2 | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.85 | 点透明度
# @PARAM add_ellipse: bool = true | 显示置信椭圆
# @PARAM ellipse_level: float = 0.95 | 椭圆置信水平
# @PARAM show_axes: bool = true | 显示中心轴线

title         = str(params.get('title', 'PCA 图'))
x_label       = str(params.get('x_label', col_x or ''))
y_label       = str(params.get('y_label', col_y or ''))
fig_width     = float(params.get('fig_width', 10))
fig_height    = float(params.get('fig_height', 8))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 12))
alpha         = float(params.get('alpha', 0.85))
add_ellipse   = str(params.get('add_ellipse', 'true')).lower() == 'true'
ellipse_level = float(params.get('ellipse_level', 0.95))
show_axes     = str(params.get('show_axes', 'true')).lower() == 'true'

sns.set_style('ticks')
sns.set_context('notebook', font_scale=font_size / 12)

# 重新设置中文字体（seaborn 的 set_style/set_context 会覆盖字体设置）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DengXian', 'DejaVu Sans']
plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False


# ====================================================================
# >>> PLOT CODE >>>
# ====================================================================

# --- 置信椭圆辅助函数 ---
def add_ellipse_patch(ax, x, y, color, level=0.95, alpha_fill=0.15):
    if len(x) < 3 or len(y) < 3:
        return
    cov = np.cov(x, y)
    if cov.shape != (2, 2) or np.isnan(cov).any():
        return
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]
    angle = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
    n_std = np.sqrt(-2 * np.log(1 - level))
    width, height = 2 * n_std * np.sqrt(vals)

    e = Ellipse(xy=(np.mean(x), np.mean(y)),
                width=width, height=height, angle=angle,
                edgecolor=color, facecolor=color, alpha=alpha_fill)
    ax.add_patch(e)


# --- 检查必要列 ---
has_x = col_x and col_x in df.columns
has_y = col_y and col_y in df.columns
has_group = col_group and col_group in df.columns

fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    if has_group:
        for i, (g, grp) in enumerate(df.groupby(col_group)):
            color = palette[i % len(palette)]
            ax.scatter(grp[col_x], grp[col_y], s=80, alpha=alpha,
                       color=color, label=str(g),
                       edgecolors='white', linewidths=0.3)
            if add_ellipse and len(grp) >= 3:
                add_ellipse_patch(ax, grp[col_x].values, grp[col_y].values,
                                  color, level=ellipse_level)
        ax.legend(fontsize=font_size - 1)
    else:
        ax.scatter(df[col_x], df[col_y], s=80, alpha=alpha,
                   color=palette[0], edgecolors='white', linewidths=0.3)

    if show_axes:
        ax.axhline(y=0, linestyle='dashed', color='#999999', linewidth=0.6)
        ax.axvline(x=0, linestyle='dashed', color='#999999', linewidth=0.6)

    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    ax.tick_params(labelsize=font_size - 1)

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