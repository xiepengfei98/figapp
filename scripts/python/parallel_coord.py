#!/usr/bin/env python3
"""
平行坐标图 (Parallel Coordinates Plot) — Python 版本
=====================================================

【图表涵义】
平行坐标图用多条平行轴展示高维数据，每条轴代表一个维度，
线条穿越表示样本在各维度的取值轨迹，用于模式识别和聚类分析。

【适用场景】
- 高维数据的模式识别和聚类趋势
- 多变量样本的分布比较
- 特征选择和变量关系探索

【数据要求】
- group: 分组变量（分类，可选）
- 其余数值列作为平行坐标轴

=== 列名映射 (columns) =======================================================
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
# 4. 列名映射 — 按列顺序: 第1列=group(分组变量,可选), 其余数值列作为平行坐标轴
# ====================================================================

_df_cols = df.columns.tolist()
col_group = _df_cols[0] if len(_df_cols) > 0 else None
col_x = col_y = col_color = col_facet = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.7 | 线透明度

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 6))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
alpha      = float(params.get('alpha', 0.7))

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

# --- 获取数值列 ---
has_group = col_group and col_group in df.columns
num_cols = [c for c in df.columns
            if c != col_group and pd.api.types.is_numeric_dtype(df[c])]

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if len(num_cols) >= 2:
    if has_group:
        groups = df[col_group].unique()
        for i, g in enumerate(groups):
            grp = df[df[col_group] == g]
            color = palette[i % len(palette)]

            # 归一化
            norm = np.zeros_like(grp[num_cols].values, dtype=float)
            for j, col_name in enumerate(num_cols):
                vals = grp[col_name].values.astype(float)
                vmin, vmax = vals.min(), vals.max()
                if vmax > vmin:
                    norm[:, j] = (vals - vmin) / (vmax - vmin)
                else:
                    norm[:, j] = 0.5

            x = np.arange(len(num_cols))
            for row in norm:
                ax.plot(x, row, color=color, alpha=alpha, linewidth=1.0)
            ax.plot(x, norm.mean(axis=0), color=color,
                    linewidth=2.5, label=str(g), alpha=0.9)
        ax.legend(fontsize=font_size - 1)
    else:
        norm = np.zeros_like(df[num_cols].values, dtype=float)
        for j, col_name in enumerate(num_cols):
            vals = df[col_name].values.astype(float)
            vmin, vmax = vals.min(), vals.max()
            if vmax > vmin:
                norm[:, j] = (vals - vmin) / (vmax - vmin)
            else:
                norm[:, j] = 0.5

        x = np.arange(len(num_cols))
        for row in norm:
            ax.plot(x, row, color=palette[0], alpha=alpha, linewidth=1.0)

    ax.set_xticks(np.arange(len(num_cols)))
    ax.set_xticklabels(num_cols, fontsize=font_size - 2)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.2, axis='x')

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    ax.text(0.5, 0.5, '请上传数据\n(需至少 2 个数值列)',
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
