import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# לוקחים מהסביבה (Railway נותן DATABASE_URL אוטומטית)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./slh_shop_core.db")

connect_args = {}
# רק ב-SQLite צריך check_same_thread
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
