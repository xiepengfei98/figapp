#!/usr/bin/env python3
"""
GO 圈图 (GO Circle Plot) — Python 版本
========================================

【图表涵义】
GO 圈图在极坐标中用条形展示 GO 富集分析结果，每个条形代表一个 GO 术语，
条形高度为富集分数，颜色区分 GO 类别（BP/MF/CC）。

【适用场景】
- GO 富集分析结果可视化
- 展示多个 GO 术语的富集程度
- 按 BP/MF/CC 类别分色展示

【数据要求】
- x: GO 术语名称（分类）
- y: 富集分数（数值）
- group: GO 类别（分类，如 BP/MF/CC）

=== 列名映射 (columns) =======================================================
  x       — GO 术语名称（分类）
  y       — 富集分数（数值）
  group   — GO 类别（分类，如 BP/MF/CC）
  facet   — 分面列（可选）

=== @PARAM 说明 ===============================================================
  所有 @PARAM 在右侧面板生成控件，出图后可调参数并重绘。
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
# 4. 列名映射 — 按列顺序: 第1列=x(GO术语), 第2列=y(富集分数), 第3列=group(GO类别)
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
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.9 | 柱体透明度

title      = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 6))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
alpha      = float(params.get('alpha', 0.9))

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
has_x = col_x and col_x in df.columns
has_y = col_y and col_y in df.columns
has_group = col_group and col_group in df.columns

if not has_x:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            col_x = c
            has_x = True
            break
if not has_y:
    for c in df.columns:
        if c != col_x and pd.api.types.is_numeric_dtype(df[c]):
            col_y = c
            has_y = True
            break
if not has_group:
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]) and c != col_x:
            col_group = c
            has_group = True
            break

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height),
                       subplot_kw={'projection': 'polar'})

if has_x and has_y:
    n_terms = len(df)
    angles = np.linspace(0, 2 * np.pi, n_terms, endpoint=False)
    bar_width = 2 * np.pi / n_terms * 0.84

    # 分类颜色映射
    if has_group:
        categories = df[col_group].unique()
        cat_colors = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}
    cat_colors_used = {}

    max_val = df[col_y].max()

    for idx, (_, row) in enumerate(df.iterrows()):
        if has_group:
            cat = row[col_group]
            color = cat_colors.get(cat, palette[0])
            cat_colors_used[cat] = color
        else:
            color = palette[idx % len(palette)]

        ax.bar(angles[idx], row[col_y], width=bar_width,
               bottom=0, color=color, edgecolor='#333333',
               linewidth=0.3, alpha=alpha)

        # 标签
        label_text = str(row[col_x])
        label_angle = np.degrees(angles[idx])
        rotation = label_angle if label_angle < 180 else label_angle - 180
        ha = 'left' if label_angle < 180 else 'right'
        ax.text(angles[idx], row[col_y] + max_val * 0.12,
                label_text, rotation=rotation, ha=ha, va='center',
                fontsize=font_size - 3, color='#333333')

    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_ylim(0, max_val * 1.6)
    ax.set_xticks([])
    ax.set_yticks([])

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=20)

    # 图例
    if has_group and len(cat_colors_used) > 0:
        handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cat_colors_used.values()]
        ax.legend(handles, list(cat_colors_used.keys()), fontsize=font_size - 1,
                  loc='upper right', bbox_to_anchor=(1.25, 1.1))

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
