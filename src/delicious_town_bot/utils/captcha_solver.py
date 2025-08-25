"""
src/delicious_town_bot/utils/captcha_solver.py

通用验证码识别工具模块
- 从根目录 .env 加载配置，无需 settings.py
- 支持申请 codekey、拉取验证码、调用打码平台、重试
"""
import io
import os
import time
import base64
import requests
from dotenv import load_dotenv
from PIL import Image

# 加载根目录 .env
load_dotenv()

class CaptchaSolver:
    """封装验证码识别流程，支持从 .env 读取配置和自定义重试次数。"""

    def __init__(self):
        # 从环境变量读取配置
        self.base_url = os.getenv("BASE_URL")
        self.api_url = os.getenv("API_URL")
        self.api_token = os.getenv("API_TOKEN")
        self.captcha_type = os.getenv("CAPTCHA_TYPE_ID")
        # 默认重试次数为 10
        self.max_retries = int(os.getenv("CAPTCHA_MAX_RETRIES", "10"))

        # HTTP 会话
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/wap/login.html",
        })

    def get_codekey(self) -> (str, str):
        """申请新的 codekey 与对应的 img_url。"""
        url = f"{self.base_url}/index.php?g=api&m=checkcode&a=makecodekey"
        resp = self.session.post(url, data={"codekey": ""})
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return data.get("codekey"), data.get("img_url")

    def fetch_captcha(self, codekey: str, img_url: str) -> Image.Image:
        """拉取验证码图片并转为灰度。"""
        full = self.base_url + img_url
        r = self.session.get(full, stream=True)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("L")

    def solve_with_api(self, img: Image.Image) -> str:
        """调用第三方打码平台获取验证码文本。"""
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        payload = {
            "token": self.api_token,
            "type": self.captcha_type,
            "image": img_b64,
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(self.api_url, json=payload, headers=headers)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 10000:
            raise RuntimeError(f"打码平台调用失败: {result}")
        detail = result.get("data", {})
        if detail.get("code") != 0 or not detail.get("data"):
            raise RuntimeError(f"打码失败: {detail}")
        return detail.get("data").strip()

    def solve(self) -> (str, str):
        """完整流程：多次重试获取正确验证码文本与 codekey。"""
        for attempt in range(1, self.max_retries + 1):
            try:
                codekey, img_url = self.get_codekey()
                img = self.fetch_captcha(codekey, img_url)
                text = self.solve_with_api(img)
                return text, codekey
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(1)
                    continue
                raise
