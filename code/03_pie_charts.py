import os
from pathlib import Path
from urllib.parse import quote_plus

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
PIC_DIR = ROOT / 'pic'
PIC_DIR.mkdir(exist_ok=True)

# 马卡龙风格配色，全部图共用，保证风格一致
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

# 非转化相关指标：字段表达式 -> (中文标题, 取值标签映射)
PIE_METRICS = {
    'new_user': ('新老用户', 'new_user', {0: '老用户', 1: '新用户'}),
    'sex': ('性别', 'sex', {'Female': '女性', 'Male': '男性'}),
    'market': ('用户地区', 'market', {1: '市场1', 2: '市场2', 3: '市场3', 4: '市场4'}),
    'device': ('访问设备', 'device', {'mobile': '移动端', 'desktop': '桌面端'}),
    'operative_system': ('操作系统', 'operative_system', {
        'windows': 'Windows', 'iOS': 'iOS', 'android': 'Android',
        'mac': 'macOS', 'linux': 'Linux', 'other': '其他',
    }),
    'source': ('流量来源', 'source', {'Direct': '直接访问', 'Seo': '搜索引擎', 'Ads': '广告投放'}),
    'age_band': ('年龄分布', (
        "CASE WHEN age <= 20 THEN '20岁及以下'"
        " WHEN age <= 30 THEN '21-30岁'"
        " WHEN age <= 40 THEN '31-40岁'"
        " ELSE '41岁及以上' END"
    ), {}),
    'activity_band': ('用户活跃度', (
        "CASE WHEN total_pages_visited < 5 THEN '低活跃度'"
        " WHEN total_pages_visited < 10 THEN '中活跃度'"
        " ELSE '高活跃度' END"
    ), {}),
}

for name, (title, expr, label_map) in PIE_METRICS.items():
    df = pd.read_sql(
        f'SELECT {expr} AS value, COUNT(*) AS n FROM user_action GROUP BY value', engine
    )
    df['label'] = df['value'].map(lambda v: label_map.get(v, v))

    fig, ax = plt.subplots(figsize=(7, 5))
    wedges, _, autotexts = ax.pie(
        df['n'],
        colors=PALETTE[:len(df)],
        startangle=90,
        counterclock=False,
        autopct='%.1f%%',
        pctdistance=0.72,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2},
        textprops={'color': TEXT_COLOR, 'fontsize': 10},
    )
    for t in autotexts:
        t.set_fontsize(10)
        t.set_color(TEXT_COLOR)

    ax.legend(
        wedges,
        [f'{lab}（{n:,}）' for lab, n in zip(df['label'], df['n'])],
        loc='center left',
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
        fontsize=9,
        labelcolor=TEXT_COLOR,
    )
    ax.set_title(f'{title}占比', fontsize=14, color=TEXT_COLOR, pad=12)

    out_path = PIC_DIR / f'pie_{name}.png'
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)
    print('已保存：', out_path)