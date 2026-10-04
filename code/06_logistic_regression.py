import os
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from dotenv import load_dotenv
from sklearn.metrics import roc_auc_score
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

# 与列联表分析保持同一转化口径
OUTCOME = 'confirmation_page'

engine = create_engine(
    'mysql+pymysql://'
    f"{os.getenv('DB_USER', 'root')}:{quote_plus(os.getenv('DB_PASSWORD'))}"
    f"@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '3306')}"
    f"/{os.getenv('DB_NAME', 'project1_users')}?charset=utf8mb4"
)

# ---------- 共线性诊断：device 与 operative_system ----------
# 两者若高度重合，同时入模会互相抢夺解释力，系数和置信区间都会变得不可用
diag = pd.read_sql(
    'SELECT device, operative_system, COUNT(*) AS n '
    'FROM user_action GROUP BY device, operative_system',
    engine,
)
diag_tab = diag.pivot(index='device', columns='operative_system', values='n').fillna(0).astype(int)
print('\n【共线性诊断】device × operative_system 频数表')
print(diag_tab.to_string())

# ---------- 读取建模数据 ----------
df = pd.read_sql(
    f'SELECT age, sex, new_user, market, device, operative_system, source, {OUTCOME} '
    f'FROM user_action',
    engine,
)

# 设定参照组：Categorical 的第一个水平 = 参照组
CATEGORY_ORDER = {
    'sex': ['Male', 'Female'],
    'market': [1, 2, 3, 4],
    'device': ['mobile', 'desktop'],
    'operative_system': ['windows', 'iOS', 'android', 'mac', 'linux', 'other'],
    'source': ['Direct', 'Seo', 'Ads'],
}
for col, order in CATEGORY_ORDER.items():
    df[col] = pd.Categorical(df[col], categories=order)

# age 保持连续（不分箱），new_user 本身是 0/1，直接作为数值变量
CONTINUOUS_TERMS = ['age', 'new_user']
TERMS = ['age', 'sex', 'new_user', 'market', 'device', 'operative_system', 'source']

# 多变量模型剔除 device：它与 operative_system 近似共线，
# 而 operative_system 是更细的划分，保留它
MODEL_TERMS = [t for t in TERMS if t != 'device']
FORMULA = f'{OUTCOME} ~ ' + ' + '.join(
    t if t in CONTINUOUS_TERMS else f'C({t})' for t in MODEL_TERMS
)


def odds_ratio_table(result):
    """把回归系数整理成 OR 表：OR > 1 表示该组转化几率高于参照组"""
    conf = result.conf_int()
    return pd.DataFrame({
        '变量': result.params.index,
        '系数': result.params.values.round(4),
        'OR': np.exp(result.params.values).round(4),
        'OR 95% 下限': np.exp(conf[0].values).round(4),
        'OR 95% 上限': np.exp(conf[1].values).round(4),
        'p值': result.pvalues.values,
    })


# ---------- 单变量模型：每个变量单独入模，作为未调整的基准 ----------
uni_tables = []
for term in TERMS:
    expr = term if term in CONTINUOUS_TERMS else f'C({term})'
    uni_res = smf.logit(f'{OUTCOME} ~ {expr}', data=df).fit(disp=0)
    tbl = odds_ratio_table(uni_res)
    tbl.insert(0, '模型变量', term)
    uni_tables.append(tbl)

uni_table = pd.concat(uni_tables, ignore_index=True)
print(f'\n{"=" * 78}\n【单变量逻辑回归】各自单独入模，未做调整')
print(uni_table.to_string(index=False, formatters={'p值': lambda v: f'{v:.3e}'}))

# ---------- 多变量模型：全部变量同时入模，互为控制 ----------
model = smf.logit(FORMULA, data=df).fit(disp=0)
multi_table = odds_ratio_table(model)

print(f'\n{"=" * 78}\n【多变量逻辑回归】{FORMULA}')
print(multi_table.to_string(index=False, formatters={'p值': lambda v: f'{v:.3e}'}))

pred = model.predict(df)
auc = roc_auc_score(df[OUTCOME], pred)
print(f'\n样本量 = {int(model.nobs)}，'
      f'McFadden 伪 R² = {model.prsquared:.4f}，'
      f'LLR 检验 p 值 = {model.llr_pvalue:.3e}，'
      f'AUC = {auc:.4f}')
print(f'基准转化率 = {df[OUTCOME].mean():.4f}')