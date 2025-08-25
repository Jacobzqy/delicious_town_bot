"""
src/delicious_town_bot/utils/auth.py

登录模块工具：
- 自动获取验证码并识别
- 处理重试逻辑
- 完成登录并返回 key
- 配置从根目录 .env 读取，无需 settings.py
"""
import os
import time
import json
import requests
from dotenv import load_dotenv

from src.delicious_town_bot.utils.captcha_solver import CaptchaSolver

# —————— 环境加载 ——————
load_dotenv()

BASE_URL = os.getenv("BASE_URL")
LOGIN_PATH = os.getenv("LOGIN_PATH", "/index.php?g=User&m=login&a=dologin")
MAX_LOGIN_RETRIES = int(os.getenv("LOGIN_MAX_RETRIES", "5"))

# 会话复用
SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/wap/login.html",
})


def do_login(username: str, password: str, max_retries: int = None) -> str:
    """
    执行登录：
      1. 获取并识别验证码（使用 CaptchaSolver）
      2. 提交登录请求
      3. 若验证码错误则重试，最多 max_retries 次
    返回：登录成功后的 key 字符串
    抛出：RuntimeError 登录失败或重试耗尽
    """
    solver = CaptchaSolver()
    retries = max_retries or MAX_LOGIN_RETRIES

    for i in range(1, retries + 1):
        # 1. 获取验证码并识别
        verify, codekey = solver.solve()
        print(f"[登录尝试 {i}/{retries}] codekey={codekey}, verify={verify}")

        # 2. 提交登录
        url = f"{BASE_URL}{LOGIN_PATH}"
        payload = {
            "user_login": username,
            "password": password,
            "verify": verify,
            "codekey": codekey,
        }
        resp = SESSION.post(url, data=payload)
        resp.raise_for_status()
        result = resp.json()

        # 3. 判断结果
        if result.get("status"):
            key = result["data"]["key"]
            print(f"登录成功，key = {key}")
            return key
        else:
            msg = result.get("msg", "未知错误")
            print(f"登录失败：{msg}")
            if "验证码错误" in msg and i < retries:
                time.sleep(1)
                continue
            raise RuntimeError(f"登录失败：{msg}")

    raise RuntimeError(f"登录失败，已尝试 {retries} 次验证码重试")


if __name__ == "__main__":
    # 简单测试
    user = os.getenv("TEST_USER")
    pwd = os.getenv("TEST_PASS")
    key = do_login(user, pwd)
    print("Obtained key:", key)
