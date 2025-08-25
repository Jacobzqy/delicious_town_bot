#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量注册小号脚本
位置：src/delicious_town_bot/scripts/register.py
"""
import io
import os
import time
import json
import base64
import requests
from PIL import Image
from dotenv import load_dotenv

# —————— 环境变量加载 ——————
load_dotenv()
API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
CAPTCHA_TYPE_ID = os.getenv("CAPTCHA_TYPE_ID")

# —————— 配置区域 ——————
BASE = "http://117.72.123.195"
JSON_PATH = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "data", "initial_accounts.json")
MAX_CAPTCHA_RETRIES = 5

# 会话复用
SESSION = requests.Session()
SESSION.verify = False  # 忽略 SSL 验证
SESSION.headers.update({
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE,
    "Referer": f"{BASE}/wap/register.html",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
})


def get_codekey():
    """申请新的 codekey 和 img_url。"""
    url = f"{BASE}/index.php?g=api&m=checkcode&a=makecodekey"
    resp = SESSION.post(url, data={"codekey": ""})
    resp.raise_for_status()
    return resp.json()["data"]["codekey"], resp.json()["data"]["img_url"]


def fetch_captcha(codekey: str, img_url: str) -> Image.Image:
    """根据 img_url 拉取验证码并转为灰度 Image。"""
    full_url = BASE + img_url
    r = SESSION.get(full_url, stream=True)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("L")


def solve_captcha_with_api(img: Image.Image) -> str:
    """调用第三方 API 打码服务，返回识别出的数字验证码。"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    payload = {
        "token": API_TOKEN,
        "type": CAPTCHA_TYPE_ID,
        "image": img_b64,
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(API_URL, headers=headers, json=payload)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") != 10000:
        raise RuntimeError(f"打码平台调用失败: {result}")
    detail = result["data"]
    if detail.get("code") != 0 or not detail.get("data"):
        raise RuntimeError(f"打码失败（内部错误）: {detail}")
    return detail["data"].strip()


def register_account(username: str, password: str):
    """
    获取验证码→识别验证码→提交注册。
    若提示“验证码错误！”，则重试（最多 MAX_CAPTCHA_RETRIES 次）。
    """
    for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
        try:
            codekey, img_url = get_codekey()
            img = fetch_captcha(codekey, img_url)
            verify = solve_captcha_with_api(img)
            print(f"[{username}] 尝试 {attempt}/{MAX_CAPTCHA_RETRIES} → codekey={codekey}, verify={verify}")

            payload = {
                "user_login": username,
                "password": password,
                "password_confirm": password,
                "mobile": "",
                "email": "",
                "codekey": codekey,
                "verify": verify,
            }
            reg_url = f"{BASE}/index.php?g=user&m=register&a=doregister"
            resp = SESSION.post(reg_url, data=payload)
            resp.raise_for_status()
            result = resp.json()

            if result.get("status"):
                print(f"[{username}] 注册成功！")
                return
            else:
                msg = result.get("msg", "")
                print(f"[{username}] 注册失败：{msg}")
                if "验证码错误" in msg and attempt < MAX_CAPTCHA_RETRIES:
                    print(f"[{username}] 验证码错误，重试…")
                    time.sleep(1)
                    continue
                break

        except Exception as e:
            print(f"[{username}] 第 {attempt} 次尝试出错：{e}")
            if attempt < MAX_CAPTCHA_RETRIES:
                time.sleep(1)
                continue
            break

    print(f"[{username}] 注册最终失败。\n")


def main():
    # 读取 JSON 列表
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        accounts = json.load(f)

    for acct in accounts:
        register_account(acct["username"], acct["password"])
        time.sleep(0.5)


if __name__ == "__main__":
    main()
