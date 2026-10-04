from pathlib import Path

import pandas as pd

# 用 __file__ 定位数据，保证从任意目录运行都能找到文件
DATA_PATH = Path(__file__).resolve().parent.parent / "用户行为分析.csv"

df = pd.read_csv(DATA_PATH)

# 数据概览
print('数据概览：')
print(df.info())

# 表头（字段名）
print('\n字段：', df.columns.tolist())

# 前 5 行数据
print('\n前 5 行数据：')
print(df.head())

# 字段类型
print('\n字段类型：')
print(df.dtypes)

# 逐个字段看取值：低基数直接列出全部取值，高基数用 describe 看分布
print('\n===== 各字段取值 =====')
for col in df.columns:
    n_unique = df[col].nunique()
    print(f'\n[{col}]  dtype={df[col].dtype}  唯一值数={n_unique}')
    if n_unique <= 20:
        print(df[col].value_counts().to_string())
    else:
        print(df[col].describe().to_string())