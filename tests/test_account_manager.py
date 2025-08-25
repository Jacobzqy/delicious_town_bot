# tests/test_account_manager.py
import json
from pathlib import Path
import pytest
from src.delicious_town_bot.utils.account_manager import AccountManager, Account

def test_refresh_first_account():
    # 1. 读取初始账号配置
    project_root = Path(__file__).parent.parent
    init_path = project_root / "data" / "initial_accounts.json"
    assert init_path.exists(), f"初始账号配置文件未找到: {init_path}"
    accounts_data = json.loads(init_path.read_text(encoding="utf-8"))
    assert isinstance(accounts_data, list) and accounts_data, "初始账号列表为空或格式不正确"

    # 2. 初始化 AccountManager 并导入第一条账号
    mgr = AccountManager()
    first = accounts_data[0]
    username = first.get("username")
    password = first.get("password")
    assert username and password, "初始账号配置缺少 username/password"

    # 尝试添加或更新该账号
    try:
        acc = mgr.add_account(username, password)
    except ValueError:
        acc_list = mgr.list_accounts()
        acc = next((a for a in acc_list if a.username == username), None)
        assert acc, f"账号 {username} 应存在于数据库"
        mgr.update_account(acc.id, password=password)

    # 3. 刷新 key 并断言返回值
    key = mgr.refresh_key(acc.id)
    assert isinstance(key, str) and key, "刷新 key 未返回有效字符串"

    # 4. 清理环境（可选）：删除测试账号
    mgr.delete_account(acc.id)
    mgr.close()
