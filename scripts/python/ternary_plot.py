#!/usr/bin/env python3
"""
三元图 (Ternary Plot) — Python 版本
======================================

【图表涵义】
三元图展示三组分数据的比例关系，三个顶点分别代表三个组分的 100%，
点在三角形内的位置反映三组分的相对比例。

【适用场景】
- 三组分数据的组成比例可视化
- 成分分析、土壤/地质学数据展示
- 基因型频率的三角分布

【数据要求】
- x: A 组分（数值，比例或绝对值）
- y: B 组分（数值）
- color: C 组分（数值）

=== 列名映射 (columns) =======================================================
  x       — A 组分（数值）
  y       — B 组分（数值）
  color   — C 组分（数值）
  group   — 分组（可选）
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
# 4. 列名映射 — 按列顺序: 第1列=x(A组分), 第2列=y(B组分), 第3列=color(C组分), 第4列=group(分组,可选), 第5列=facet(分面,可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_color = _df_cols[2] if len(_df_cols) > 2 else None
col_group = _df_cols[3] if len(_df_cols) > 3 else None
col_facet = _df_cols[4] if len(_df_cols) > 4 else None
col_label = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.85 | 点透明度
# @PARAM label_a: str = A | A 组分标签
# @PARAM label_b: str = B | B 组分标签
# @PARAM label_c: str = C | C 组分标签

title    = str(params.get('title', ''))
fig_width  = float(params.get('fig_width', 10))
fig_height = float(params.get('fig_height', 8))
dpi        = int(params.get('dpi', 300))
font_size  = int(params.get('font_size', 12))
alpha      = float(params.get('alpha', 0.85))
label_a    = str(params.get('label_a', 'A'))
label_b    = str(params.get('label_b', 'B'))
label_c    = str(params.get('label_c', 'C'))

sns.set_style('whitegrid')
sns.set_context('notebook', font_scale=font_size / 12)

# 重新设置中文字体（seaborn 的 set_style/set_context 会覆盖字体设置）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DengXian', 'DejaVu Sans']
plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False


# ====================================================================
# 三元坐标转换函数
# ====================================================================

def to_ternary(a, b, c):
    s = a + b + c
    x = np.where(s > 0, 0.5 * (2 * b + c) / s, 0.5)
    y = np.where(s > 0, (np.sqrt(3) / 2) * c / s, 0)
    return x, y


# ====================================================================
# >>> PLOT CODE >>> — 在此处编写您的绘图代码
#     可用变量: df, col_x, col_y, col_group, col_color, col_facet,
#               col_label, col_size, palette, title, x_label, y_label,
#               fig_width, fig_height, dpi, font_size, alpha
# ====================================================================

# --- 检查必要列 ---
has_x = col_x and col_x in df.columns
has_y = col_y and col_y in df.columns
has_color_col = col_color and col_color in df.columns
has_group = col_group and col_group in df.columns

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if has_x and has_y and has_color_col:
    # 绘制三角形框架
    corners = np.array([[0, 0], [1, 0], [0.5, np.sqrt(3) / 2], [0, 0]])
    ax.plot(corners[:, 0], corners[:, 1], 'k-', linewidth=0.8)

    # 网格线
    for i in range(1, 10):
        t = i / 10
        ax.plot([t / 2, 1 - t / 2],
                [t * np.sqrt(3) / 2, t * np.sqrt(3) / 2],
                color='grey', linewidth=0.3, linestyle=':')
        ax.plot([t / 2, 1 - t],
                [t * np.sqrt(3) / 2, 0],
                color='grey', linewidth=0.3, linestyle=':')
        ax.plot([t, 1 - t / 2],
                [0, t * np.sqrt(3) / 2],
                color='grey', linewidth=0.3, linestyle=':')

    # 顶点标签
    ax.text(0, -0.05, label_a, fontsize=font_size, ha='center', va='top')
    ax.text(1, -0.05, label_b, fontsize=font_size, ha='center', va='top')
    ax.text(0.5, np.sqrt(3) / 2 + 0.03, label_c,
            fontsize=font_size, ha='center', va='bottom')

    # 转换并绘制数据点
    xs, ys = to_ternary(df[col_x].values, df[col_y].values,
                        df[col_color].values)

    if has_group:
        for i, (g, grp) in enumerate(df.groupby(col_group)):
            idx = grp.index
            color = palette[i % len(palette)]
            ax.scatter(xs[idx], ys[idx], s=80, alpha=alpha,
                       color=color, edgecolors='white',
                       linewidths=0.3, label=str(g))
        ax.legend(fontsize=font_size - 1)
    else:
        ax.scatter(xs, ys, s=80, alpha=alpha, color=palette[0],
                   edgecolors='white', linewidths=0.3)

    ax.set_aspect('equal')
    ax.axis('off')

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)

    if col_facet and col_facet in df.columns:
        print(f"提示: 分面列 '{col_facet}' 已指定，但当前为单轴绘图")

else:
    msg = '请上传数据并配置列映射\n(columns → x=A, y=B, color=C)'
    ax.text(0.5, 0.5, msg, ha='center', va='center',
            fontsize=14, color='#999', transform=ax.transAxes)

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
