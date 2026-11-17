#!/usr/bin/env python3
"""宽数据转长数据：将列式变量转换为行式观测。"""
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

# 自动分离标识列和数值列
# 非数值列作为标识列，数值列作为待熔化变量列
all_cols = df.columns.tolist()
id_cols = []
value_cols = []

for col in all_cols:
    if pd.api.types.is_numeric_dtype(df[col]):
        value_cols.append(col)
    else:
        id_cols.append(col)

# 如果所有列都是数值，保留第一列作为标识列
if not id_cols:
    id_cols = [all_cols[0]]
    value_cols = all_cols[1:]

if not value_cols:
    print("错误: 没有检测到数值列可供转换")
    sys.exit(1)

long = df.melt(id_vars=id_cols, value_vars=value_cols,
               var_name='variable', value_name='value')
long = long.dropna(subset=['value'])

long.to_csv(output_file, index=False, encoding='utf-8-sig')

n_rows, n_cols = long.shape
print(f"宽→长: {n_rows} 行 x {n_cols} 列")
print(f"标识列({len(id_cols)}): {', '.join(id_cols[:5])}{'...' if len(id_cols) > 5 else ''}")
print(f"熔化 {len(value_cols)} 个变量列")
