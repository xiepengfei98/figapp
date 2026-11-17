#!/usr/bin/env python3
"""
散点图 (Scatter Plot) — Python 版本
====================================

【图表涵义】
散点图展示两个连续变量之间的关系，支持分组着色、气泡大小映射和回归线叠加，
直观呈现变量间的相关性、趋势和异常点。

【适用场景】
- 探索两个连续变量的相关关系和趋势
- 展示分组数据的聚类模式
- 通过气泡大小映射第三维数据
- 叠加回归线和置信区间辅助判断相关性

【数据要求】
- x: X 轴数值变量（数值）
- y: Y 轴数值变量（数值）
- group: 分组变量（可选），按组着色
- size: 气泡大小变量（可选），映射点大小
- label: 标签变量（可选），标注点

=== 列名映射 (columns) =======================================================
  x       — X 轴数值变量（数值）
  y       — Y 轴数值变量（数值）
  group   — 分组变量（可选，用于颜色区分）
  size    — 气泡大小变量（可选，映射点大小）
  label   — 标签变量（可选，标注点）
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
from scipy import stats


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
# 4. 列名映射 — 按列顺序: 第1列=x(X轴数值), 第2列=y(Y轴数值), 第3列=group(分组,可选), 第4列=size(气泡大小,可选)
# ====================================================================
_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_size = _df_cols[3] if len(_df_cols) > 3 else None
col_color = col_facet = col_label = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.8 | 点透明度
# @PARAM point_size: float = 60 | 固定点大小（未映射 size 时）
# @PARAM add_smooth: bool = false | 添加回归线
# @PARAM add_cor_label: bool = true | 显示相关系数
# @PARAM cor_method: select = pearson | 相关方法 [pearson,spearman]
# @PARAM log_x: bool = false | X 轴对数刻度
# @PARAM log_y: bool = false | Y 轴对数刻度

title         = str(params.get('title', ''))
x_label       = str(params.get('x_label', col_x or ''))
y_label       = str(params.get('y_label', col_y or ''))
fig_width     = float(params.get('fig_width', 10))
fig_height    = float(params.get('fig_height', 8))
dpi           = int(params.get('dpi', 300))
font_size     = int(params.get('font_size', 12))
alpha         = float(params.get('alpha', 0.8))
point_size    = float(params.get('point_size', 60))
add_smooth    = str(params.get('add_smooth', 'false')).lower() == 'true'
add_cor_label = str(params.get('add_cor_label', 'true')).lower() == 'true'
cor_method    = str(params.get('cor_method', 'pearson'))
log_x         = str(params.get('log_x', 'false')).lower() == 'true'
log_y         = str(params.get('log_y', 'false')).lower() == 'true'

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
    if not has_x:
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                col_x = c
                has_x = True
                break
    if not has_y:
        for c in df.columns:
            if c != col_x and pd.api.types.is_numeric_dtype(df[c]):
                col_y = c
                has_y = True
                break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y:
    has_group = col_group and col_group in df.columns
    has_size_col = col_size and col_size in df.columns

    # 绘制散点
    if has_group:
        scatter = sns.scatterplot(
            data=df, x=col_x, y=col_y,
            hue=col_group, size=col_size if has_size_col else None,
            sizes=(20, 300) if has_size_col else None,
            palette=palette, edgecolor='#333333',
            linewidth=0.4, alpha=alpha, legend='auto', ax=ax)
    elif has_size_col:
        scatter = sns.scatterplot(
            data=df, x=col_x, y=col_y, size=col_size,
            sizes=(20, 300), color=palette[0],
            edgecolor='#333333', linewidth=0.4, alpha=alpha, ax=ax)
    else:
        ax.scatter(df[col_x], df[col_y], s=point_size,
                  facecolor=palette[0], edgecolor='#333333',
                  linewidth=0.4, alpha=alpha)

    # 回归线
    if add_smooth:
        if has_group:
            for g in df[col_group].unique():
                subset = df[df[col_group] == g]
                sns.regplot(data=subset, x=col_x, y=col_y,
                           scatter=False, ci=95,
                           line_kws={'linewidth': 1.5}, ax=ax)
        else:
            sns.regplot(data=df, x=col_x, y=col_y,
                       scatter=False, ci=95, color=palette[1],
                       line_kws={'linewidth': 1.5}, ax=ax)

    # 相关系数标签
    if add_cor_label:
        valid = df[[col_x, col_y]].dropna()
        x_vals = valid[col_x].values
        y_vals = valid[col_y].values
        if len(x_vals) > 2:
            if cor_method == 'pearson':
                r, p = stats.pearsonr(x_vals, y_vals)
            else:
                r, p = stats.spearmanr(x_vals, y_vals)
            ax.text(0.05, 0.95,
                   f'{cor_method} r = {r:.3f}\np = {p:.4f}',
                   transform=ax.transAxes, fontsize=font_size - 1,
                   verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # 标签
    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)

    # 标题
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    # 对数刻度
    if log_x:
        ax.set_xscale('log')
    if log_y:
        ax.set_yscale('log')

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
