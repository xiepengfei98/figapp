#!/usr/bin/env python3
"""长数据转宽数据：将行式观测转换为列式变量。"""
import sys
import pandas as pd
import numpy as np

input_file = sys.argv[1]
output_file = sys.argv[2]

# 自动检测编码
encodings = ['utf-8', 'gbk', 'gb18030', 'latin-1']
df = None
for enc in encodings:
    try:
        df = pd.read_csv(input_file, encoding=enc)
        break
    except (UnicodeDecodeError, TypeError):
        continue

if df is None:
    print("错误: 无法识别文件编码")
    sys.exit(1)

cols = df.columns.tolist()

# 自动检测变量名列和数值列
var_col = None
val_col = None

# 优先按列名匹配
for col in cols:
    name_lower = col.lower()
    if name_lower in ('variable', 'var', 'name', '变量'):
        var_col = col
    elif name_lower in ('value', 'val', '值', '数值'):
        val_col = col

# 如果按名称没找到，按类型检测
if var_col is None or val_col is None:
    for col in cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            if val_col is None:
                val_col = col
        else:
            if var_col is None:
                var_col = col

# 最后兜底：按位置
if var_col is None:
    var_col = cols[1] if len(cols) > 1 else cols[0]
if val_col is None:
    val_col = cols[2] if len(cols) > 2 else cols[-1]

# 剩余所有列为标识列
id_cols = [col for col in cols if col not in [var_col, val_col]]

if not id_cols:
    print("错误: 没有标识列可供分组")
    sys.exit(1)

wide = df.pivot(index=id_cols, columns=var_col, values=val_col)
wide = wide.reset_index()
wide.columns.name = None

wide.to_csv(output_file, index=False, encoding='utf-8-sig')

n_rows, n_cols = wide.shape
print(f"长→宽: {n_rows} 行 x {n_cols} 列")
print(f"标识列({len(id_cols)}): {', '.join(id_cols[:5])}{'...' if len(id_cols) > 5 else ''}")
print(f"变量列: {var_col}, 数值列: {val_col}")
