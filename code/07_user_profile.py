import os
from pathlib import Path
from urllib.parse import quote_plus

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
PIC_DIR = ROOT / 'pic'
PIC_DIR.mkdir(exist_ok=True)

# 与其他脚本同一套配色与字体，保证图片风格一致
PALETTE = ['#FF9B9B', '#FFD93D', '#6BCB77', '#87CEEB', '#DDA0DD', '#FBC78F']
TEXT_COLOR = '#333333'
SUB_COLOR = '#888888'

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

# 画像特征：(特征名, SQL 表达式, 取值标签)
# 每个特征只取转化人群里占比最高的那一个取值
# 不含活跃度：转化人群里"低活跃度"结构性为 0，且高活跃度与转化互为定义
# 不含 device：它与 operative_system 近似共线，保留更细的那个
PROFILE_FEATURES = [
    ('性别', 'sex', {'Female': '女性', 'Male': '男性'}),
    ('年龄段', AGE_BAND_EXPR, {}),
    ('新老用户', 'new_user', {0: '老用户', 1: '新用户'}),
    ('用户地区', 'market', {1: '市场1', 2: '市场2', 3: '市场3', 4: '市场4'}),
    ('操作系统', 'operative_system', {
        'windows': 'Windows', 'iOS': 'iOS', 'android': 'Android',
        'mac': 'macOS', 'linux': 'Linux', 'other': '其他',
    }),
    ('流量来源', 'source', {
        'Direct': '直接访问', 'Seo': '搜索引擎', 'Ads': '广告投放',
    }),
]

total = int(pd.read_sql(
    'SELECT COUNT(*) AS n FROM user_action WHERE confirmation_page = 1', engine
)['n'].iloc[0])
print('转化人群会话数 =', total)

features = []
for name, expr, label_map in PROFILE_FEATURES:
    df = pd.read_sql(
        f'SELECT {expr} AS v, COUNT(*) AS n FROM user_action '
        f'WHERE confirmation_page = 1 GROUP BY v ORDER BY n DESC',
        engine,
    )
    top_v, top_n = df['v'].iloc[0], int(df['n'].iloc[0])
    runner_n = int(df['n'].iloc[1])
    features.append((name, label_map.get(top_v, top_v), top_n, runner_n))
    print(f'{name}：{label_map.get(top_v, top_v)} {top_n}（{top_n / total * 100:.2f}%），'
          f'次高 {label_map.get(df["v"].iloc[1], df["v"].iloc[1])} {runner_n}')


def tangent_points(p1, r1, p2, r2, r):
    """求与两个已放置圆都外切、半径为 r 的圆的圆心候选位置（最多两个）"""
    d = float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))
    if d < 1e-12:
        return []
    a, b = r1 + r, r2 + r
    if d > a + b or d < abs(a - b):
        return []
    x = (d * d + a * a - b * b) / (2 * d)
    h2 = a * a - x * x
    if h2 < 0:
        return []
    h = np.sqrt(h2)
    ux, uy = (p2[0] - p1[0]) / d, (p2[1] - p1[1]) / d
    bx, by = p1[0] + x * ux, p1[1] + x * uy
    return [(bx - h * uy, by + h * ux), (bx + h * uy, by - h * ux)]


def pack_circles(radii):
    """把若干小圆排成最紧凑的一簇：按半径从大到小逐个放，
    每个圆都在所有可行外切位置里挑"让整簇包络半径最小"的落点。
    最后把整簇平移居中，返回 (排布, 包络半径)。"""
    placed = []
    for r in radii:
        if not placed:
            placed.append((0.0, 0.0, r))
            continue

        candidates = [(0.0, 0.0)]
        for px, py, pr in placed:
            for k in range(360):
                theta = 2 * np.pi * k / 360
                candidates.append((px + (pr + r) * np.cos(theta),
                                   py + (pr + r) * np.sin(theta)))
        for i in range(len(placed)):
            for j in range(i + 1, len(placed)):
                candidates.extend(tangent_points(
                    placed[i][:2], placed[i][2], placed[j][:2], placed[j][2], r
                ))

        best = None
        for x, y in candidates:
            if any(np.hypot(x - px, y - py) < r + pr - 1e-9 for px, py, pr in placed):
                continue
            enc = max(np.hypot(x, y) + r,
                      max(np.hypot(px, py) + pr for px, py, pr in placed))
            if best is None or enc < best[0] - 1e-12:
                best = (enc, x, y)
        if best is None:
            return None
        placed.append((best[1], best[2], r))

    # 平移让整簇居中
    cx = (max(x + r for x, y, r in placed) + min(x - r for x, y, r in placed)) / 2
    cy = (max(y + r for x, y, r in placed) + min(y - r for x, y, r in placed)) / 2
    placed = [(x - cx, y - cy, r) for x, y, r in placed]
    enclosing = max(np.hypot(x, y) + r for x, y, r in placed)
    return placed, enclosing


# 半径取 sqrt(人数)，面积就与人数严格成正比；再统一缩放到大圆内
CONTAINER_R = 1.0
radii = [np.sqrt(n) for _, _, n, _ in features]
order = np.argsort(radii)[::-1]
placed, enclosing = pack_circles([radii[i] for i in order])
scale = CONTAINER_R / enclosing

layout = [None] * len(features)
for slot, idx in enumerate(order):
    x, y, r = placed[slot]
    layout[idx] = (x * scale, y * scale, r * scale)

fill = sum(r * r for _, _, r in layout) / CONTAINER_R ** 2
print(f'统一缩放系数 = {scale:.4f}，小圆面积合计占大圆 {fill * 100:.1f}%')

# 面积校验：任意两圆的面积比应等于人数比
for i in range(len(features)):
    for j in range(i + 1, len(features)):
        area_ratio = layout[i][2] ** 2 / layout[j][2] ** 2
        n_ratio = features[i][2] / features[j][2]
        assert abs(area_ratio - n_ratio) < 1e-9

fig, ax = plt.subplots(figsize=(12, 12))

# 大圆：全部转化会话
ax.add_patch(plt.Circle((0, 0), CONTAINER_R, facecolor='#FBFBFB',
                        edgecolor='#DDDDDD', linewidth=2, zorder=1))

for i, ((name, value, n, runner_n), (x, y, r)) in enumerate(zip(features, layout)):
    ax.add_patch(plt.Circle((x, y), r, facecolor=PALETTE[i % len(PALETTE)],
                            edgecolor='white', linewidth=2.5, zorder=2))
    ax.text(x, y + 0.30 * r, name, ha='center', va='center',
            fontsize=12, color='#6B6B6B', zorder=3)
    ax.text(x, y + 0.02 * r, value, ha='center', va='center',
            fontsize=17, color=TEXT_COLOR, zorder=3)
    ax.text(x, y - 0.34 * r, f'{n:,}（{n / total * 100:.1f}%）',
            ha='center', va='center', fontsize=11, color='#5A5A5A', zorder=3)

ax.set_title(f'转化人群画像：到达确认页的 {total:,} 次会话',
             fontsize=20, color=TEXT_COLOR, pad=18)
ax.text(0, -CONTAINER_R - 0.16,
        '每个特征取转化人群中占比最高的那一个取值，小圆面积与该取值的会话数成正比',
        ha='center', va='center', fontsize=12, color=SUB_COLOR)
ax.text(0, -CONTAINER_R - 0.27,
        '六个特征是同一批人的不同切面，彼此重叠，因此面积可横向比较，但不构成大圆的划分',
        ha='center', va='center', fontsize=11, color=SUB_COLOR)

ax.set_xlim(-1.2, 1.2)
ax.set_ylim(-1.45, 1.15)
ax.set_aspect('equal')
ax.axis('off')

out_path = PIC_DIR / 'profile_bubble.png'
fig.savefig(out_path, bbox_inches='tight')
plt.close(fig)
print('已保存：', out_path)