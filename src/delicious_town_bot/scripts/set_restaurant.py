"""
一次性：为每个账号设置餐厅名
读取 data/initial_accounts.json 的 restaurant 字段
"""

import json, time, requests, os
from pathlib import Path
from dotenv import load_dotenv
from src.delicious_town_bot.utils.account_manager import AccountManager

load_dotenv()
BASE_URL = os.getenv("BASE_URL")

SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/wap/res/new_game.html",
})

def set_name(key: str, name: str) -> bool:
    url = f"{BASE_URL}/index.php?g=Res&m=index&a=add_game"
    resp = SESSION.post(url, data={"key": key, "res_name": name})
    if resp.ok and resp.json().get("status"):
        return True
    print("❌", name, resp.text)
    return False

def main():
    data_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "initial_accounts.json"
    accounts_json = json.loads(data_path.read_text(encoding="utf-8"))

    mgr = AccountManager()
    for item in accounts_json[29:]:
        name     = item.get("restaurant")
        username = item.get("username")
        acc = next((a for a in mgr.list_accounts() if a.username == username), None)
        if not acc or not acc.key:
            print(f"跳过 {username}，数据库无记录或缺少 key")
            continue
        # 已有餐厅名则跳过
        if acc.restaurant:
            print(f"已存在餐厅 {acc.restaurant}，跳过")
            continue
        ok = set_name(acc.key, name)
        if ok:
            mgr.update_account(acc.id, restaurant=name)
            print(f"✅ {username} → {name}")
        time.sleep(0.3)

    mgr.close()

if __name__ == "__main__":
    main()