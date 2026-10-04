from pathlib import Path

import pandas as pd

# 用 __file__ 定位数据，保证从任意目录运行都能找到文件
DATA_PATH = Path(__file__).resolve().parent.parent / "用户行为分析.csv"

df = pd.read_csv(DATA_PATH)

print('\n清洗前维度：', df.shape)

# 1) total_pages_visited：仅保留小于 99 分位数的值
q99 = df['total_pages_visited'].quantile(0.99)
print('\ntotal_pages_visited 的 99 分位数：', q99)
df = df[df['total_pages_visited'] < q99]
print('剔除 total_pages_visited >= 99 分位数后维度：', df.shape)

# 2) 含哨兵值 '0' 的字段：剔除这些行
SENTINEL_COLS = ['sex', 'device', 'operative_system', 'source']
sentinel_mask = df[SENTINEL_COLS].isin(['0']).any(axis=1)
print('\n命中哨兵值的行数：', int(sentinel_mask.sum()))
df = df[~sentinel_mask]
print('剔除哨兵值行后维度：', df.shape)

# 3) age：保留 0-100 的数据
age_mask = df['age'].between(0, 100)
print('\nage 不在 0-100 区间内的行数：', int((~age_mask).sum()))
df = df[age_mask]
print('剔除 age 异常值后维度：', df.shape)

print('\n清洗后维度：', df.shape)

# 保存清洗后的数据
OUT_PATH = Path(__file__).resolve().parent.parent / "用户行为分析_cleaned.csv"
df.to_csv(OUT_PATH, index=False)
print('已保存至：', OUT_PATH)