from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, func, Text
)
from .session import Base

class Account(Base):
    __tablename__ = "accounts"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    username   = Column(String(64), unique=True, nullable=False)
    password   = Column(String(128), nullable=False)      # 明文或加密后存储
    key        = Column(String(64), nullable=True)        # 登录后拿到的 key
    cookie     = Column(Text,    nullable=True)           # 如 PHPSESSID 等
    last_login = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active  = Column(Boolean, default=True, nullable=False)