#!/usr/bin/env python3
"""
共线性图 (Collinearity / VIF Chart) — Python 版本
===================================================

【图表涵义】
共线性图以棒棒糖图展示各变量的方差膨胀因子(VIF)，VIF > 5 表示中等共线性，
VIF > 10 表示严重共线性，需考虑变量选择或正则化。

【适用场景】
- 回归分析前检查自变量间的多重共线性
- 变量筛选和特征选择
- 统计建模中的诊断检查

【数据要求】
预计算 VIF 格式：
- x: 变量名列（分类）
- y: VIF 值列（数值）

或原始数据格式：全部为数值列，自动计算 VIF。

=== 列名映射 (columns) =======================================================
  x       — 变量名列（分类）
  y       — VIF 值列（数值）
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
# 4. 列名映射 — 按列顺序: 第1列=x(变量名), 第2列=y(VIF值), 第3列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_facet = _df_cols[2] if len(_df_cols) > 2 else None
col_group = col_color = col_label = col_size = col_subgroup = None


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

title    = str(params.get('title', ''))
x_label  = str(params.get('x_label', ''))
y_label  = str(params.get('y_label', ''))
fig_width  = float(params.get('fig_width', 8))
fig_height = float(params.get('fig_height', 6))
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
# ====================================================================

# 检查是否有预计算 VIF 列
has_var_col = col_x and col_x in df.columns
has_vif_col = col_y and col_y in df.columns

fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_var_col and has_vif_col:
    # 预计算 VIF 格式
    vif_df = df[[col_x, col_y]].copy()
    vif_df.columns = ['variable', 'vif']
    vif_df = vif_df.sort_values('vif', ascending=True)

elif not has_var_col:
    # 原始数值格式，自动计算 VIF
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) >= 2:
        from sklearn.linear_model import LinearRegression
        X_data = df[numeric_cols].dropna().values
        vif_results = []
        for i, name in enumerate(numeric_cols):
            y = X_data[:, i]
            X_rest = np.delete(X_data, i, axis=1)
            model = LinearRegression()
            model.fit(X_rest, y)
            r_sq = model.score(X_rest, y)
            vif = 1.0 / (1.0 - r_sq + 1e-9)
            vif_results.append({'variable': name, 'vif': vif})
        vif_df = pd.DataFrame(vif_results).sort_values('vif', ascending=True)
    else:
        ax.text(0.5, 0.5, '需要至少 2 个数值列\n以自动计算 VIF',
                ha='center', va='center', fontsize=14, color='#999',
                transform=ax.transAxes)
        vif_df = pd.DataFrame()

else:
    ax.text(0.5, 0.5, '请配置列映射\n(columns → x=变量名, y=VIF)',
            ha='center', va='center', fontsize=14, color='#999',
            transform=ax.transAxes)
    vif_df = pd.DataFrame()

if len(vif_df) > 0:
    y_range = range(len(vif_df))

    # 根据 VIF 阈值设置颜色
    def get_color(v):
        if v >= 10: return '#E64B35'
        if v >= 5: return '#F39B7F'
        return '#4DBBD5'

    colors = [get_color(v) for v in vif_df['vif']]

    # 棒棒糖图
    ax.hlines(y=y_range, xmin=0, xmax=vif_df['vif'].values,
              color='#CCCCCC', linewidth=2, alpha=0.7)
    ax.scatter(vif_df['vif'].values, y_range, s=80,
              color=colors, edgecolors='white', linewidths=0.5, zorder=5)

    # 阈值参考线
    ax.axvline(x=5, color='#F39B7F', linestyle='--', linewidth=0.8, alpha=0.6)
    ax.axvline(x=10, color='#E64B35', linestyle='--', linewidth=0.8, alpha=0.6)

    ax.set_yticks(y_range)
    ax.set_yticklabels(vif_df['variable'].values, fontsize=font_size - 1)
    ax.set_xlabel(x_label or 'VIF Value', fontsize=font_size)
    ax.set_ylabel(y_label or 'Variable', fontsize=font_size)

    # X 轴从 0 开始
    xlim_max = max(vif_df['vif'].max() * 1.2, 12)
    ax.set_xlim(0, xlim_max)

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
