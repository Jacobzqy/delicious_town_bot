"""
账号管理工具
- list_accounts: 查询所有账号
- add_account: 新增账号
- delete_account: 删除账号
- update_account: 修改密码/启用状态
- refresh_key: 用登录工具刷新并保存 key + cookie + last_login
"""
from datetime import datetime
from sqlalchemy.orm import Session
from src.delicious_town_bot.db.session import DBSession, init_db
from src.delicious_town_bot.db.models import Account
from src.delicious_town_bot.utils.auth import do_login
import json

# 确保表已创建
init_db()

class AccountManager:
    def __init__(self):
        # 每次操作都从 scoped_session 获取
        self.db: Session = DBSession()

    def list_accounts(self):
        return self.db.query(Account).all()

    def add_account(self, username: str, password: str):
        acc = self.db.query(Account).filter_by(username=username).first()
        if acc:
            raise ValueError(f"账号 {username} 已存在")
        acc = Account(username=username, password=password)
        self.db.add(acc)
        self.db.commit()
        return acc

    def delete_account(self, account_id: int):
        acc = self.db.query(Account).get(account_id)
        if not acc:
            raise ValueError(f"找不到 id={account_id}")
        self.db.delete(acc)
        self.db.commit()

    def get_account(self, account_id: int):
        """根据ID获取账号信息"""
        acc = self.db.query(Account).get(account_id)
        if not acc:
            raise ValueError(f"找不到 id={account_id}")
        return acc

    def update_account(self, account_id: int, **fields):
        acc = self.db.query(Account).get(account_id)
        if not acc:
            raise ValueError(f"找不到 id={account_id}")
        for k, v in fields.items():
            setattr(acc, k, v)
        self.db.commit()
        return acc

    def refresh_key(self, account_id: int):
        acc = self.db.query(Account).get(account_id)
        if not acc:
            raise ValueError(f"找不到 id={account_id}")
        # 调用登录工具
        key = do_login(acc.username, acc.password)
        # 假设 do_login 内部不返回 cookie，这里保持默认 '123'
        acc.key = key
        acc.last_login = datetime.now()
        self.db.commit()
        return key

    def close(self):
        self.db.close()
