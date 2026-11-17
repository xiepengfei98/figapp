#!/usr/bin/env python3
"""
环形饼图 / 嵌套饼图 (Nested Donut Chart) — Python 版本
=========================================================

【图表涵义】
环形饼图在饼图基础上挖空中心，形成甜甜圈造型。多个环形饼图并排展示
各组的类别构成，中心镂空使视觉更简洁，适合展示比例数据。

【适用场景】
- 比较多组数据的类别构成差异（环形样式）
- 展示不同部门的预算分配
- 替代传统饼图，视觉效果更现代

【数据要求】
- x: 类别变量（扇形标签）
- y: 数值变量（扇形大小）
- group: 分组变量（每个组生成一个环形图）

=== 列名映射 (columns) =======================================================
  x       — 类别变量（分类）
  y       — 数值变量（数值）
  group   — 分组变量（分类）
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
# 4. 列名映射 — 按列顺序: 第1列=x, 第2列=y, 第3列=group, 第4列=facet(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_group = _df_cols[2] if len(_df_cols) > 2 else None
col_facet = _df_cols[3] if len(_df_cols) > 3 else None
col_color = col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 14 | 图片宽度（英寸）
# @PARAM fig_height: float = 5 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM show_pct: bool = true | 显示百分比
# @PARAM hole_size: float = 0.4 | 中心空洞比例（0-0.7）
# @PARAM start_angle: float = 90 | 起始角度

title       = str(params.get('title', ''))
fig_width   = float(params.get('fig_width', 14))
fig_height  = float(params.get('fig_height', 5))
dpi         = int(params.get('dpi', 300))
font_size   = int(params.get('font_size', 12))
show_pct    = str(params.get('show_pct', 'true')).lower() == 'true'
hole_size   = float(params.get('hole_size', 0.4))
start_angle = float(params.get('start_angle', 90))

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
        if not pd.api.types.is_numeric_dtype(df[c]) and c != col_group:
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
if has_x and has_y and has_group:
    groups = sorted(df[col_group].unique())
    n_groups = len(groups)
    categories = sorted(df[col_x].unique())
    cat_colors = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}
    fig_width_adj = max(fig_width, n_groups * 3)

    fig, axes = plt.subplots(1, n_groups, figsize=(fig_width_adj, fig_height))
    if n_groups == 1:
        axes = [axes]

    for idx, group in enumerate(groups):
        group_data = df[df[col_group] == group].sort_values(col_x)
        group_values = group_data[col_y].values
        group_labels = group_data[col_x].tolist()
        group_colors = [cat_colors.get(cat, palette[0]) for cat in group_labels]

        autopct_val = '%1.1f%%' if show_pct else None
        wedges, texts, autotexts = axes[idx].pie(
            group_values, labels=None, autopct=autopct_val,
            startangle=start_angle, colors=group_colors,
            pctdistance=0.75, textprops={'fontsize': font_size - 1},
            wedgeprops={'width': 1 - hole_size, 'edgecolor': 'white', 'linewidth': 1.0})
        axes[idx].set_title(str(group), fontsize=font_size, fontweight='bold')

    # 统一图例
    handles = [plt.Rectangle((0, 0), 1, 1, color=cat_colors[cat]) for cat in categories]
    fig.legend(handles, list(categories), title=col_x,
               loc='center left', bbox_to_anchor=(1.02, 0.5),
               fontsize=font_size - 1, title_fontsize=font_size)

    if title:
        fig.suptitle(title, fontsize=font_size + 2, fontweight='bold')

    fig.tight_layout(rect=[0, 0, 0.88, 0.95])

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但已使用 group 分组")

else:
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    missing = []
    if not has_x: missing.append('x')
    if not has_y: missing.append('y')
    if not has_group: missing.append('group')
    ax.text(0.5, 0.5, f'请上传数据并配置列映射\n(columns → {", ".join(missing)})',
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
