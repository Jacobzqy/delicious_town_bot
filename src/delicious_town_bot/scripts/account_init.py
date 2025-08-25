#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量导入 initial_accounts.json 到数据库
"""

import json
from pathlib import Path
import typer

from src.delicious_town_bot.utils.account_manager import AccountManager

app = typer.Typer(add_help_option=False)

DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "initial_accounts.json"

@app.command()
def main(
    path: Path = typer.Argument(
        DEFAULT_PATH,
        exists=True,
        dir_okay=False,
        help="包含 username/password 列表的 JSON 文件"
    )
):
    mgr = AccountManager()
    added = updated = 0

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        typer.echo("❌ JSON 格式错误，应为列表")
        raise typer.Exit(code=1)

    for item in data:
        username = item.get("username")
        password = item.get("password")
        if not username or not password:
            typer.echo(f"⚠️ 跳过缺少字段的条目: {item}")
            continue
        try:
            mgr.add_account(username, password)
            added += 1
        except ValueError:  # 已存在 → 更新密码
            acc_list = mgr.list_accounts()
            acc = next((a for a in acc_list if a.username == username), None)
            if acc:
                mgr.update_account(acc.id, password=password)
                updated += 1

    mgr.close()
    typer.secho(f"✅ 导入完成：新增 {added} 个，更新 {updated} 个", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
