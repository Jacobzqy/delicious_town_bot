import json
from pathlib import Path
import typer

from delicious_town_bot.db.session import engine, SessionLocal, Base
from delicious_town_bot.db.models import Account

app = typer.Typer(help="初始化账号数据：从 JSON 导入 username/password")

@app.command("init")
def account_init(
    json_path: Path = Path("data/initial_accounts.json")
):
    """从 data/initial_accounts.json 批量导入账号"""
    # 1. 确保表已创建
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 2. 读取 JSON
    if not json_path.exists():
        typer.secho(f"❌ 文件不存在：{json_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    added = 0
    for entry in data:
        username = entry.get("username")
        password = entry.get("password")
        if not username or not password:
            continue

        # 3. 插入或更新
        acc = db.query(Account).filter_by(username=username).first()
        if acc:
            acc.password = password
        else:
            acc = Account(
                username=username,
                password=password
            )
            db.add(acc)
        added += 1

    db.commit()
    db.close()
    typer.secho(f"✅ 已导入/更新 {added} 个账号", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()