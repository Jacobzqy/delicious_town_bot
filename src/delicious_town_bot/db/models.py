from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from src.delicious_town_bot.db.session import Base, init_db

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    key = Column(String(128), nullable=True)
    cookie = Column(String(256), nullable=True, default='123')
    restaurant = Column(String(64))
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Account id={self.id} username={self.username} key={self.key}>"


class FriendCache(Base):
    __tablename__ = 'friend_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    friend_id = Column(Integer, nullable=False)  # 好友的餐厅ID
    friend_name = Column(String(64), nullable=False)
    friend_level = Column(Integer, nullable=True)
    friend_avatar = Column(String(128), nullable=True)
    last_updated = Column(DateTime, nullable=False)

    # 建立与Account的关系
    account = relationship("Account", backref="friends_cache")

    def __repr__(self):
        return f"<FriendCache account_id={self.account_id} friend_id={self.friend_id} friend_name={self.friend_name}>"


class SpecialFoodTask(Base):
    __tablename__ = 'special_food_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    task_date = Column(Date, nullable=False)  # 任务日期（每日重置）
    completed = Column(Boolean, default=False, nullable=False)  # 是否完成
    food_name = Column(String(64), nullable=True)  # 购买的特价菜名称
    quantity = Column(Integer, nullable=True)  # 购买数量
    gold_spent = Column(Integer, nullable=True)  # 花费金币
    completed_at = Column(DateTime, nullable=True)  # 完成时间
    error_message = Column(Text, nullable=True)  # 错误信息（如果失败）

    # 建立与Account的关系
    account = relationship("Account", backref="special_food_tasks")

    def __repr__(self):
        return f"<SpecialFoodTask account_id={self.account_id} date={self.task_date} completed={self.completed}>"


# 若直接运行此文件，可初始化数据库表
if __name__ == '__main__':
    init_db()  # type: ignore
