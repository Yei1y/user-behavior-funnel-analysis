import os
from pathlib import Path
from urllib.parse import quote_plus

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from dotenv import load_dotenv
from scipy import stats
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
PIC_DIR = ROOT / 'pic'
PIC_DIR.mkdir(exist_ok=True)

# 与饼图脚本保持同一套配色与字体，保证图片风格一致
PALETTE = ['#FF9B9B', '#FFD93D', '#6BCB77', '#87CEEB', '#DDA0DD', '#FBC78F']
TEXT_COLOR = '#333333'

plt.rcParams.update({
    'font.sans-serif': ['Microsoft YaHei'],
    'axes.unicode_minus': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.dpi': 150,
})

load_dotenv(ROOT / '.env')

engine = create_engine(
    'mysql+pymysql://'
    f"{os.getenv('DB_USER', 'root')}:{quote_plus(os.getenv('DB_PASSWORD'))}"
    f"@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '3306')}"
    f"/{os.getenv('DB_NAME', 'project1_users')}?charset=utf8mb4"
)

AGE_BAND_EXPR = (
    "CASE WHEN age <= 20 THEN '20岁及以下'"
    " WHEN age <= 30 THEN '21-30岁'"
    " WHEN age <= 40 THEN '31-40岁'"
    " ELSE '41岁及以上' END"
)

# 维度 -> SQL 表达式
DIM_EXPR = {
    'sex': 'sex',
    'new_user': 'new_user',
    'source': 'source',
    'device': 'device',
    'operative_system': 'operative_system',
    'age_band': AGE_BAND_EXPR,
}
# 维度 -> 取值标签
DIM_LABEL = {
    'sex': {'Female': '女性', 'Male': '男性'},
    'new_user': {0: '老用户', 1: '新用户'},
    'source': {'Direct': '直接访问', 'Seo': '搜索引擎', 'Ads': '广告投放'},
    'device': {'mobile': '移动端', 'desktop': '桌面端'},
    'operative_system': {
        'windows': 'Windows', 'iOS': 'iOS', 'android': 'Android',
        'mac': 'macOS', 'linux': 'Linux', 'other': '其他',
    },
    'age_band': {},
}
# 维度 -> 取值排序（横轴顺序固定，避免每次画出来顺序不同）
DIM_ORDER = {
    'sex': ['Female', 'Male'],
    'new_user': [0, 1],
    'source': ['Direct', 'Seo', 'Ads'],
    'device': ['mobile', 'desktop'],
    'operative_system': ['windows', 'iOS', 'android', 'mac', 'linux', 'other'],
    'age_band': ['20岁及以下', '21-30岁', '31-40岁', '41岁及以上'],
}
# 维度 -> 图题用的中文名
DIM_CN = {
    'sex': '性别',
    'new_user': '新老用户',
    'source': '流量来源',
    'device': '访问设备',
    'operative_system': '操作系统',
    'age_band': '年龄段',
}

# (文件名, 分组维度, 横轴维度) —— 每张图画两者的整体转化率
# 交互项检验结果：sex×operative_system 的 LR 卡方 (54.88) 远高于 sex×device (10.11)，
# 且 device 在已含 operative_system 的模型里增量不显著 (p=0.192)，故用操作系统替换设备
CROSS_CHARTS = [
    ('sex_source', 'sex', 'source'),
    ('newuser_source', 'new_user', 'source'),
    ('sex_os', 'sex', 'operative_system'),
    ('sex_age', 'sex', 'age_band'),
]


# ---------- 交互项检验：上面这四张图为什么是这四个组合的依据 ----------
# 主效应模型只放变量本身，交叉图的价值在于捕捉交互。所以对候选交互项做
# 似然比检验，只有显著改善拟合的交互才值得画成图；不显著的画出来就是一组平行线。
MODEL_TERMS = ['age', 'sex', 'new_user', 'market', 'operative_system', 'source']
MODEL_COLUMNS = MODEL_TERMS + ['device']
BASE_FORMULA = 'confirmation_page ~ ' + ' + '.join(
    t if t in ('age', 'new_user') else f'C({t})' for t in MODEL_TERMS
)

model_df = pd.read_sql(
    f'SELECT {", ".join(MODEL_COLUMNS)}, confirmation_page FROM user_action',
    engine,
)
MODEL_CATEGORY_ORDER = {
    'sex': ['Male', 'Female'],
    'market': [1, 2, 3, 4],
    'device': ['mobile', 'desktop'],
    'operative_system': ['windows', 'iOS', 'android', 'mac', 'linux', 'other'],
}
for col, order in MODEL_CATEGORY_ORDER.items():
    model_df[col] = pd.Categorical(model_df[col], categories=order)


def _term(name):
    """连续变量直接入模，分类变量包一层 C()"""
    return name if name in ('age', 'new_user') else f'C({name})'


def _benjamini_hochberg(p_values):
    """BH 法校正 p 值，一次做多个检验时控制错误发现率"""
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    ranked = p[order] * len(p) / np.arange(1, len(p) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty(len(p))
    adjusted[order] = np.clip(ranked, 0, 1)
    return adjusted


# 候选交互项：先覆盖当前四张图对应的组合，再放几个备选供判断
CANDIDATE_INTERACTIONS = [
    ('sex', 'source'),
    ('new_user', 'source'),
    ('sex', 'operative_system'),
    ('sex', 'age'),
    ('sex', 'device'),
    ('age', 'operative_system'),
    ('source', 'age'),
    ('new_user', 'age'),
    ('new_user', 'sex'),
    ('device', 'source'),
    ('source', 'market'),
    ('new_user', 'market'),
    ('age', 'market'),
    ('sex', 'market'),
]

base_res = smf.logit(BASE_FORMULA, data=model_df).fit(disp=0)

interaction_rows = []
for a, b in CANDIDATE_INTERACTIONS:
    res = smf.logit(f'{BASE_FORMULA} + {_term(a)}:{_term(b)}', data=model_df).fit(disp=0)
    lr = 2 * (res.llr - base_res.llr)
    dof = int(res.df_model - base_res.df_model)
    interaction_rows.append({
        '交互项': f'{a} × {b}',
        'LR 卡方': round(lr, 2),
        '自由度': dof,
        'p值': stats.chi2.sf(lr, dof),
        '伪R²': round(res.prsquared, 4),
    })

# device 在已经含有 operative_system 的模型里是否还有增量，
# 这是"device 只是 operative_system 的粗化、不含额外信息"的直接检验
device_res = smf.logit(BASE_FORMULA + ' + C(device)', data=model_df).fit(disp=0)
lr = 2 * (device_res.llr - base_res.llr)
dof = int(device_res.df_model - base_res.df_model)
interaction_rows.append({
    '交互项': '（主效应）device 增量',
    'LR 卡方': round(lr, 2),
    '自由度': dof,
    'p值': stats.chi2.sf(lr, dof),
    '伪R²': round(device_res.prsquared, 4),
})

interaction_table = pd.DataFrame(interaction_rows).sort_values('p值').reset_index(drop=True)
interaction_table['BH校正p值'] = _benjamini_hochberg(interaction_table['p值'].values)

print(f'主效应模型：{BASE_FORMULA}')
print(f'主效应模型伪 R² = {base_res.prsquared:.4f}，参数个数 = {int(base_res.df_model) + 1}')
print('\n【交互项似然比检验】逐个加入主效应模型，看是否显著改善拟合')
print(interaction_table.to_string(index=False, formatters={
    'p值': lambda v: f'{v:.3e}',
    'BH校正p值': lambda v: f'{v:.3e}',
}))
print()

for fname, hue_dim, x_dim in CROSS_CHARTS:
    sql = (
        f'SELECT {DIM_EXPR[hue_dim]} AS hue, {DIM_EXPR[x_dim]} AS x, '
        f'COUNT(*) AS n, SUM(confirmation_page) / COUNT(*) AS rate '
        f'FROM user_action GROUP BY hue, x'
    )
    df = pd.read_sql(sql, engine)

    pivot = df.pivot(index='x', columns='hue', values='rate')
    pivot = pivot.reindex(index=DIM_ORDER[x_dim], columns=DIM_ORDER[hue_dim]).fillna(0) * 100

    x = np.arange(len(pivot.index))
    n_hue = len(pivot.columns)
    width = 0.8 / n_hue

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, col in enumerate(pivot.columns):
        offset = (i - (n_hue - 1) / 2) * width
        bars = ax.bar(
            x + offset, pivot[col].values, width,
            label=DIM_LABEL[hue_dim].get(col, col),
            color=PALETTE[i], edgecolor='white', linewidth=1,
        )
        ax.bar_label(bars, fmt='%.2f%%', fontsize=8, padding=2, color=TEXT_COLOR)

    ax.set_xticks(x)
    ax.set_xticklabels([DIM_LABEL[x_dim].get(v, v) for v in pivot.index], fontsize=10)
    ax.set_ylabel('整体转化率（%）', fontsize=11, color=TEXT_COLOR)
    ax.set_title(
        f'{DIM_CN[hue_dim]} × {DIM_CN[x_dim]} 的整体转化率',
        fontsize=13, color=TEXT_COLOR, pad=12,
    )

    ax.legend(frameon=False, fontsize=10, labelcolor=TEXT_COLOR)
    ax.grid(axis='y', linestyle='--', alpha=0.35, color='#CCCCCC')
    ax.set_axisbelow(True)
    for side in ['top', 'right']:
        ax.spines[side].set_visible(False)
    for side in ['left', 'bottom']:
        ax.spines[side].set_color('#CCCCCC')

    fig.tight_layout()
    out_path = PIC_DIR / f'cross_{fname}.png'
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)
    print('已保存：', out_path)