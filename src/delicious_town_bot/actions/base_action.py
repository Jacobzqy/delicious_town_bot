import time
import requests
from typing import Any, Dict, Optional

class BusinessLogicError(Exception):
    """当服务器返回 status: false 时抛出此异常。"""
    pass

class BaseAction:
    """
    所有游戏操作的基类。
    封装了通用的会话管理、网络请求、重试逻辑和数据清洗。
    """

    def __init__(
            self,
            key: str,
            base_url: str,
            cookie: Optional[Dict[str, str]] = None,
            max_retries: int = 3,
            timeout: int = 8,
    ):
        """
        初始化一个操作实例。

        :param key: 用户的会话密钥 (key)。
        :param cookie: 用户的会话 Cookie (例如 {"PHPSESSID": "..."})。
        :param base_url: 该操作模块对应的基础 URL。
        :param max_retries: 单次请求的最大重试次数。
        :param timeout: 请求超时时间（秒）。
        """
        if not key or not cookie:
            raise ValueError("必须提供有效的 key 和 cookie。")

        self.key = key
        self.cookie = cookie
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout

        # 初始化 requests.Session，管理会话和通用 Headers
        self.http_client = requests.Session()
        self.http_client.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })

        if self.cookie:
            self.http_client.cookies.update(self.cookie)

    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        私有的通用请求方法。现在只对网络错误进行重试。
        """
        if 'data' in kwargs and isinstance(kwargs['data'], dict):
            kwargs['data']['key'] = self.key

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.http_client.request(method, url, timeout=self.timeout, **kwargs)
                response.raise_for_status()

                raw_json = response.json()
                if raw_json.get("status") is not True:
                    error_message = raw_json.get('msg', '无错误信息')
                    raise BusinessLogicError(error_message)

                return raw_json
            except requests.RequestException as e:
                print(f"[Warn] 网络请求 {method} {url} 第 {attempt}/{self.max_retries} 次失败: {e}")
                last_exception = e
                time.sleep(1)

        raise ConnectionError(f"接口 {url} 网络连续失败 {self.max_retries} 次后放弃。最后一次错误: {last_exception}")

    def post(self, action_path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """发送 POST 请求。action_path 可以是 'a=action' 或 'm=Module&a=action'。"""
        if data is None:
            data = {}
        # 自动拼接 URL
        url = f"{self.base_url}&{action_path}"
        return self._request("post", url, data=data)

    def get(self, action_path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        【新增】发送 GET 请求。action_path 可以是 'a=action' 或 'm=Module&a=action'。
        """
        if params is None: params = {}
        # GET 请求的 key 通常放在 URL 参数里
        if 'key' not in params:
            params['key'] = self.key

        url = f"{self.base_url}&{action_path}"
        # _request 方法通过 **kwargs 接收 params
        return self._request("get", url, params=params)

    @staticmethod
    def dictify(obj: Any) -> Dict[str, Any]:
        """
        工具函数：将服务器可能返回的 list[dict] 或 dict 统一转成 dict，便于安全访问。
        如果输入是列表，则取第一个元素（如果它是字典的话）。
        如果输入不是字典，则返回空字典。
        """
        if isinstance(obj, list):
            obj = obj[0] if obj and isinstance(obj[0], dict) else {}
        return obj if isinstance(obj, dict) else {}