#!/usr/bin/env python3
"""
动画图 (Animated Scatter Plot) — Python 版本
=============================================

【图表涵义】
动画图展示随时间变化的散点轨迹，用动画展示数据在时间维度上的动态变化，
支持分组着色和轨迹连线的渐隐效果。

【适用场景】
- 展示数据在时间维度上的动态变化过程
- 时间序列数据的空间轨迹演变
- 报告或演示中的动态可视化

【数据要求】
- x: X 轴坐标（数值）
- y: Y 轴坐标（数值）
- label: 时间变量（数值/有序）
- group: 分组变量（可选）

=== 列名映射 (columns) =======================================================
  x       — X 轴坐标（数值）
  y       — Y 轴坐标（数值）
  label   — 时间变量（用于动画帧）
  group   — 分组变量（可选，用于颜色区分）
  facet   — 分面列（可选）

注意：此脚本会额外输出动画 GIF 文件到输出目录。
"""

import sys
import json
from pathlib import Path

import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
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
output_gif = output_file.with_suffix('.gif')
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
# 4. 列名映射 — 按列顺序: 第1列=x, 第2列=y, 第3列=label, 第4列=group(可选)
# ====================================================================

_df_cols = df.columns.tolist()
col_x = _df_cols[0] if len(_df_cols) > 0 else None
col_y = _df_cols[1] if len(_df_cols) > 1 else None
col_label = _df_cols[2] if len(_df_cols) > 2 else None
col_group = _df_cols[3] if len(_df_cols) > 3 else None
col_color = col_facet = col_size = col_subgroup = None


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 8 | 图片宽度（英寸）
# @PARAM fig_height: float = 6 | 图片高度（英寸）
# @PARAM dpi: int = 150 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.9 | 点透明度
# @PARAM interval: int = 200 | 帧间隔（毫秒）

title       = str(params.get('title', ''))
x_label     = str(params.get('x_label', col_x or ''))
y_label     = str(params.get('y_label', col_y or ''))
fig_width   = float(params.get('fig_width', 8))
fig_height  = float(params.get('fig_height', 6))
dpi         = int(params.get('dpi', 150))
font_size   = int(params.get('font_size', 12))
alpha       = float(params.get('alpha', 0.9))
interval    = int(params.get('interval', 200))

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
has_time = col_label and col_label in df.columns

if not has_x or not has_y or not has_time:
    message = '请上传数据并配置列映射\n(columns → x, y, label=时间)'
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.text(0.5, 0.5, message, ha='center', va='center',
            fontsize=14, color='#999', transform=ax.transAxes)
    gif_saved = False
    # 仍然保存提示图片，确保 output_file 被创建
    plt.tight_layout()
    fig.savefig(output_file, dpi=dpi, bbox_inches='tight', facecolor='white')
    fig.savefig(output_pdf, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
else:
    has_group = col_group and col_group in df.columns

    time_steps = sorted(df[col_label].unique())
    groups = sorted(df[col_group].unique()) if has_group else []

    # 全局坐标范围
    x_min, x_max = df[col_x].min(), df[col_x].max()
    y_min, y_max = df[col_y].min(), df[col_y].max()
    x_pad = (x_max - x_min) * 0.1 if x_max != x_min else 1
    y_pad = (y_max - y_min) * 0.1 if y_max != y_min else 1

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.set_xlabel(x_label or col_x, fontsize=font_size)
    ax.set_ylabel(y_label or col_y, fontsize=font_size)

    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)
    ax.tick_params(labelsize=font_size - 1)

    # 初始化散点对象
    scatters = []
    if has_group:
        for i, g in enumerate(groups):
            scat = ax.scatter([], [], s=80, alpha=alpha,
                            color=palette[i % len(palette)],
                            edgecolors='white', linewidths=0.3, label=str(g))
            scatters.append(scat)
        ax.legend(fontsize=font_size - 1)
    else:
        scat = ax.scatter([], [], s=80, alpha=alpha,
                         color=palette[0], edgecolors='white', linewidths=0.3)
        scatters.append(scat)

    # 轨迹线
    trails = []
    if has_group:
        for i, g in enumerate(groups):
            line, = ax.plot([], [], '-', color=palette[i % len(palette)],
                           alpha=0.3, linewidth=1)
            trails.append(line)
    else:
        line, = ax.plot([], [], '-', color=palette[0], alpha=0.3, linewidth=1)
        trails.append(line)

    time_text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                       fontsize=font_size, va='top', ha='left',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    def animate(frame_idx):
        t = time_steps[frame_idx]
        time_text.set_text(f"{col_label}: {t}")
        frame_data = df[df[col_label] == t]
        artists = [time_text]

        if has_group:
            for i, g in enumerate(groups):
                g_data = frame_data[frame_data[col_group] == g]
                scatters[i].set_offsets(
                    np.column_stack([g_data[col_x].values, g_data[col_y].values])
                    if len(g_data) > 0 else np.empty((0, 2)))

                hist = df[(df[col_label].isin(time_steps[:frame_idx + 1]))
                         & (df[col_group] == g)].sort_values(col_label)
                trails[i].set_data(hist[col_x].values, hist[col_y].values)
                artists.extend([scatters[i], trails[i]])
        else:
            scatters[0].set_offsets(
                np.column_stack([frame_data[col_x].values, frame_data[col_y].values])
                if len(frame_data) > 0 else np.empty((0, 2)))
            hist = df[df[col_label].isin(time_steps[:frame_idx + 1])].sort_values(col_label)
            trails[0].set_data(hist[col_x].values, hist[col_y].values)
            artists.extend([scatters[0], trails[0]])

        return artists

    ani = animation.FuncAnimation(fig, animate, frames=len(time_steps),
                                 interval=interval, blit=True, repeat=True)

    # 保存 GIF
    try:
        ani.save(output_gif, writer='pillow', dpi=dpi)
        print(f"GIF saved to: {output_gif.name}")
    except Exception as e:
        print(f"GIF 保存失败（需要 pillow 库）: {e}")

    gif_saved = True

# <<< PLOT CODE <<<
# ====================================================================


# ====================================================================
# 6. 保存输出（请勿修改此部分）
# ====================================================================

if gif_saved:
    plt.tight_layout()
    fig.savefig(output_file, dpi=dpi, bbox_inches='tight', facecolor='white')
    fig.savefig(output_pdf, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

print(f"输出: {output_file.name}")
