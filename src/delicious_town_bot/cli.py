import typer
from typing import Optional

from src.delicious_town_bot.utils.account_manager import AccountManager

app = typer.Typer(help="Delicious Town Bot CLI")

# 原有命令（run_task, gui…）保持不变…


# accounts 子命令组
accounts_app = typer.Typer(help="账号管理")
app.add_typer(accounts_app, name="accounts")


@accounts_app.command("list")
def list_accounts():
    """
    列出所有账号及其状态
    """
    mgr = AccountManager()
    accs = mgr.list_accounts()
    if not accs:
        typer.echo("当前无任何账号。")
    else:
        fmt = "{:<4} {:<16} {:<16} {:<6} {:<20} {}"
        typer.echo(fmt.format("ID", "用户名", "餐厅", "Key?", "最后登录", "Cookie"))
        for a in accs:
            has_key = "Y" if a.key else "N"
            last = a.last_login.strftime("%Y-%m-%d %H:%M:%S") if a.last_login else "-"
            typer.echo(fmt.format(a.id, a.username, has_key, last, (a.cookie or "")[:16]+"…"))
    mgr.close()


@accounts_app.command("add")
def add_account(
    username: str = typer.Option(..., help="新账号用户名"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="新账号密码"),
):
    """
    新增一个账号
    """
    mgr = AccountManager()
    try:
        acc = mgr.add_account(username, password)
        typer.secho(f"✅ 添加成功：ID={acc.id}，用户名={acc.username}", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(f"⚠️ {e}", fg=typer.colors.YELLOW)
    finally:
        mgr.close()


@accounts_app.command("delete")
def delete_account(
    account_id: int = typer.Argument(..., help="要删除的账号 ID"),
    force: bool = typer.Option(False, "--yes", "-y", help="跳过确认直接删除"),
):
    """
    删除指定 ID 的账号
    """
    if not force:
        confirm = typer.confirm(f"确定要删除账号 ID={account_id} 吗？")
        if not confirm:
            typer.echo("已取消。")
            raise typer.Exit()
    mgr = AccountManager()
    try:
        mgr.delete_account(account_id)
        typer.secho(f"✅ ID={account_id} 删除成功", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(f"❌ {e}", fg=typer.colors.RED)
    finally:
        mgr.close()


@accounts_app.command("refresh")
def refresh_key(
    account_id: Optional[int] = typer.Argument(None, help="要刷新的账号 ID，留空则全部刷新"),
):
    """
    刷新单个或所有账号的 key
    """
    mgr = AccountManager()
    ids = [account_id] if account_id is not None else [a.id for a in mgr.list_accounts()]
    for aid in ids:
        typer.echo(f"🔄 刷新 ID={aid} …", nl=False)
        new = mgr.refresh_key(aid)
        if new:
            typer.secho(f" 成功，key={new}", fg=typer.colors.GREEN)
        else:
            typer.secho(" 失败", fg=typer.colors.YELLOW)
    mgr.close()


if __name__ == "__main__":
    app()
