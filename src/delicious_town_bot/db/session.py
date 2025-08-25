import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from dotenv import load_dotenv

# 加载根目录 .env
load_dotenv()

# 从环境变量获取数据库 URL，默认 sqlite 文件存于 data/delicious_town_bot.db
DB_URL = os.getenv("DB_URL", "sqlite:///./data/delicious_town_bot.db")

# 如果是 SQLite，并且使用相对路径，则基于项目根目录计算绝对路径
from pathlib import Path
if DB_URL.startswith("sqlite"):
    # 提取相对文件路径部分
    rel = DB_URL.split("///", 1)[1]
    # 计算项目根目录：session.py 位于 src/delicious_town_bot/db
    project_root = Path(__file__).resolve().parents[3]
    # 拼接绝对路径
    abs_path = project_root / rel.lstrip("./")
    # 确保目录存在
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    # 替换 DB_URL 为绝对
    DB_URL = f"sqlite:///{abs_path}"

# 如果使用 SQLite，确保目录存在
if DB_URL.startswith("sqlite"):
    # 解析路径
    path = DB_URL.split("///", 1)[1]
    dirpath = os.path.dirname(path)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

# 引擎：sqlite 或其他数据库
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
    echo=False,
)

# 会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
# 线程/协程安全的 Session
DBSession = scoped_session(SessionLocal)

# 基类
Base = declarative_base()


# 运行时调用，创建所有表
def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(accounts)"))
        cols = [row['name'] for row in result.mappings()]
        if 'restaurant' not in cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN restaurant TEXT"))
    print("✅ 数据库表已创建（或已存在）")