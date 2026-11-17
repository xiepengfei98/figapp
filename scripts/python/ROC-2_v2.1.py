#!/usr/bin/env python3
"""
ROC 曲线 (Receiver Operating Characteristic Curve) — Python 版本
===============================================================

【图表涵义】
ROC 曲线以假阳性率（1-特异性）为横轴、真阳性率（敏感性）为纵轴，
展示分类模型在不同阈值下的性能。AUC 越大表示模型性能越好。

【适用场景】
- 分类模型的性能评估
- 诊断试验的准确性评估
- 多模型性能对比

【数据要求】
- 第一列：样本名（将被忽略）
- 第二列：分组（二分类，两类）
- 其余列：基因表达值（每列一个基因）

=== 列名映射 (columns) =======================================================
  未使用外部列映射，脚本自动读取数据格式。

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

from sklearn.metrics import roc_curve, auc


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
# 4. 数据格式处理 — 自动识别并确保二分类
# ====================================================================
if df.shape[1] < 3:
    raise ValueError("数据至少需要3列：样本名、分组、一个或多个基因。")

group_col = df.columns[1]
gene_cols = df.columns[2:].tolist()
sample_col = df.columns[0]

# 检查分组是否为二分类
labels = df[group_col].unique()
if len(labels) != 2:
    raise ValueError(f"分组列 '{group_col}' 必须包含两个类别，当前有 {len(labels)} 个：{labels}")

# 将分组编码为 0/1（按出现顺序：第一个为0，第二个为1）
# 后续自动调整方向确保 AUC > 0.5，因此编码顺序不影响最终图形
label_map = {labels[0]: 0, labels[1]: 1}
y_true = df[group_col].map(label_map).values

# 剔除缺失值
df_clean = df[[sample_col, group_col] + gene_cols].dropna()
y_true = df_clean[group_col].map(label_map).values


# ====================================================================
# 5. 提取绘图参数（请勿修改此部分，@PARAM 声明决定了右侧面板的控件）
# ====================================================================

# @PARAM title: str = ROC Curves | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 9 | 图片宽度（英寸）
# @PARAM fig_height: float = 7 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM show_diagonal: bool = true | 显示对角线

title          = str(params.get('title', 'ROC Curves'))
x_label        = str(params.get('x_label', ''))
y_label        = str(params.get('y_label', ''))
fig_width      = float(params.get('fig_width', 9))
fig_height     = float(params.get('fig_height', 7))
dpi            = int(params.get('dpi', 300))
font_size      = int(params.get('font_size', 12))
show_diagonal  = str(params.get('show_diagonal', 'true')).lower() == 'true'

sns.set_style('ticks')
sns.set_context('notebook', font_scale=font_size / 12)

# 重新设置中文字体（seaborn 的 set_style/set_context 会覆盖字体设置）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DengXian', 'DejaVu Sans']
plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False


# ====================================================================
# >>> PLOT CODE >>> — 在此处编写您的绘图代码
# ====================================================================

# MODIFIED: 计算每个基因的 ROC 曲线，自动调整方向使 AUC > 0.5
roc_data = []
auc_values = {}

for idx, gene in enumerate(gene_cols):
    scores = df_clean[gene].values
    if len(scores) == 0:
        continue
    
    # 计算原始 ROC
    fpr, tpr, thresholds = roc_curve(y_true, scores)
    roc_auc = auc(fpr, tpr)
    
    # 若 AUC < 0.5，反转表达值方向（相当于将预测方向反转）
    if roc_auc < 0.5:
        scores = -scores
        fpr, tpr, thresholds = roc_curve(y_true, scores)
        roc_auc = auc(fpr, tpr)
        # 注意：此时 AUC 应变为 1 - 原 AUC，确保 > 0.5
    
    gene_df = pd.DataFrame({
        'fpr': fpr,
        'tpr': tpr,
        'gene': gene,
        'auc': roc_auc
    })
    roc_data.append(gene_df)
    auc_values[gene] = roc_auc

# 合并所有基因的 ROC 数据
if roc_data:
    roc_all = pd.concat(roc_data, ignore_index=True)
else:
    roc_all = pd.DataFrame()

# --- 绘图 ---
fig, ax = plt.subplots(figsize=(fig_width, fig_height))

if not roc_all.empty:
    # 绘制每条基因的 ROC 曲线
    for i, gene in enumerate(gene_cols):
        if gene not in auc_values:
            continue
        color = palette[i % len(palette)]
        gene_roc = roc_all[roc_all['gene'] == gene]
        ax.plot(gene_roc['fpr'], gene_roc['tpr'], color=color,
                linewidth=2, alpha=0.9,
                label=f"{gene} (AUC={auc_values[gene]:.3f})")
    
    if show_diagonal:
        ax.plot([0, 1], [0, 1], color='#999999',
                linestyle='--', linewidth=1)
    
    ax.set_xlabel(x_label or 'False Positive Rate (1 - Specificity)',
                  fontsize=font_size)
    ax.set_ylabel(y_label or 'True Positive Rate (Sensitivity)',
                  fontsize=font_size)
    ax.legend(fontsize=font_size - 1, loc='lower right')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=12)
else:
    msg = '没有基因数据可画 ROC 曲线'
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