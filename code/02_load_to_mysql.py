import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent

# 口令从 .env 读取，不写死在代码里，避免提交 git 时泄露
load_dotenv(ROOT / ".env")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "project1_users")
TABLE = "user_action"

if not DB_PASSWORD:
    raise SystemExit("未读到 DB_PASSWORD，请检查项目根目录的 .env 文件")

engine = create_engine(
    "mysql+pymysql://"
    f"{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

df = pd.read_csv(ROOT / "用户行为分析_cleaned.csv")
print('\n待入库数据维度：', df.shape)

# 建表语句里显式指定字段类型，便于后续在数据库里直接写 SQL
DDL = f"""
DROP TABLE IF EXISTS {TABLE};
CREATE TABLE {TABLE} (
    new_user            TINYINT     COMMENT '是否新用户，1=新 0=老',
    age                 TINYINT     COMMENT '年龄',
    sex                 VARCHAR(10) COMMENT '性别',
    market              TINYINT     COMMENT '市场编号',
    device              VARCHAR(20) COMMENT '设备类型',
    operative_system    VARCHAR(20) COMMENT '操作系统',
    source              VARCHAR(20) COMMENT '流量来源渠道',
    total_pages_visited SMALLINT    COMMENT '本次会话浏览页面总数',
    home_page           TINYINT     COMMENT '是否到达首页',
    listing_page        TINYINT     COMMENT '是否到达列表页',
    product_page        TINYINT     COMMENT '是否到达商品详情页',
    payment_page        TINYINT     COMMENT '是否到达支付页',
    confirmation_page   TINYINT     COMMENT '是否到达确认页'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='电商会话行为数据';
"""

with engine.begin() as conn:
    for stmt in [s for s in DDL.split(';') if s.strip()]:
        conn.execute(text(stmt))
print(f'\n已新建表 {TABLE}')

df.to_sql(TABLE, engine, if_exists='append', index=False, chunksize=5000)

with engine.connect() as conn:
    n_db = conn.execute(text(f'SELECT COUNT(*) FROM {TABLE}')).scalar()
print(f'\n表 {TABLE} 实际行数：', n_db)
print('入库前数据行数：', len(df))