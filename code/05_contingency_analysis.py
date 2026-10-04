import os
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

# 转化口径：confirmation_page = 1 表示走完漏斗到达确认页
# 若要看"到达支付页"，把这里改成 'payment_page' 即可
OUTCOME = 'confirmation_page'

engine = create_engine(
    'mysql+pymysql://'
    f"{os.getenv('DB_USER', 'root')}:{quote_plus(os.getenv('DB_PASSWORD'))}"
    f"@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '3306')}"
    f"/{os.getenv('DB_NAME', 'project1_users')}?charset=utf8mb4"
)

AGE_BAND = (
    "CASE WHEN age <= 20 THEN '20岁及以下'"
    " WHEN age <= 30 THEN '21-30岁'"
    " WHEN age <= 40 THEN '31-40岁'"
    " ELSE '41岁及以上' END"
)
ACTIVITY_BAND = (
    "CASE WHEN total_pages_visited < 5 THEN '低活跃度'"
    " WHEN total_pages_visited < 10 THEN '中活跃度'"
    " ELSE '高活跃度' END"
)

# 维度名 -> SQL 表达式
DIM_EXPR = {
    '性别': 'sex',
    '年龄段': AGE_BAND,
    '用户地区': 'market',
    '访问设备': 'device',
    '操作系统': 'operative_system',
    '流量来源': 'source',
    '新老用户': 'new_user',
    '活跃度': ACTIVITY_BAND,
}
# 维度名 -> 取值顺序
DIM_ORDER = {
    '性别': ['Female', 'Male'],
    '年龄段': ['20岁及以下', '21-30岁', '31-40岁', '41岁及以上'],
    '用户地区': [1, 2, 3, 4],
    '访问设备': ['mobile', 'desktop'],
    '操作系统': ['windows', 'iOS', 'android', 'mac', 'linux', 'other'],
    '流量来源': ['Direct', 'Seo', 'Ads'],
    '新老用户': [0, 1],
    '活跃度': ['低活跃度', '中活跃度', '高活跃度'],
}


def benjamini_hochberg(p_values):
    """BH 法校正 p 值：多重检验下控制错误发现率"""
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty(n)
    adjusted[order] = np.clip(ranked, 0, 1)
    return adjusted


summary_rows = []

for dim_name, expr in DIM_EXPR.items():
    df = pd.read_sql(
        f'SELECT {expr} AS dim, {OUTCOME} AS y, COUNT(*) AS n '
        f'FROM user_action GROUP BY dim, y',
        engine,
    )

    # 列联表：行 = 维度取值，列 = 未转化 / 转化
    table = df.pivot(index='dim', columns='y', values='n')
    table = table.reindex(index=DIM_ORDER[dim_name], columns=[0, 1]).fillna(0).astype(int)

    total = table.sum(axis=1)
    table.columns = ['未转化', '转化']
    table['合计'] = total
    table['转化率'] = (table['转化'] / table['合计'] * 100).round(2).astype(str) + '%'

    print(f'\n{"=" * 60}\n【{dim_name}】交叉表')
    print(table)

    # 卡方检验：2 x k 列联表，统一不做 Yates 连续性修正（n 很大时影响可忽略）
    chi2, p, dof, expected = stats.chi2_contingency(table[['未转化', '转化']].values, correction=False)
    n_total = int(total.sum())
    min_expected = expected.min()
    cramers_v = np.sqrt(chi2 / (n_total * (min(table[['未转化', '转化']].shape) - 1)))

    print(f'卡方统计量 = {chi2:.2f}，自由度 = {dof}，p 值 = {p:.3e}，'
          f"Cramér's V = {cramers_v:.4f}，最小期望频数 = {min_expected:.1f}，样本量 = {n_total}")

    summary_rows.append({
        '维度': dim_name,
        '卡方统计量': round(chi2, 2),
        '自由度': dof,
        'p值': p,
        'BH校正p值': np.nan,
        "Cramér's V": round(cramers_v, 4),
        '最小期望频数': round(min_expected, 1),
        '样本量': n_total,
    })

summary = pd.DataFrame(summary_rows)
summary['BH校正p值'] = benjamini_hochberg(summary['p值'].values)
summary = summary.sort_values('p值').reset_index(drop=True)

print(f'\n{"=" * 60}\n【汇总】各维度与"{OUTCOME}"的列联表检验（按 p 值升序）')
print(summary.to_string(index=False, formatters={
    'p值': lambda v: f'{v:.3e}',
    'BH校正p值': lambda v: f'{v:.3e}',
}))