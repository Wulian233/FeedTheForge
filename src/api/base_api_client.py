import httpx

from services.http_config_service import HttpConfigService
from utils.dns_utils import DnsUtils


class BaseApiClient:
    base_url = None
    try_times = 3

    def __init__(self, base_url=None, headers=None):
        default_headers = {
            "User-Agent": HttpConfigService.user_agent,
            "Accept-Language": "zh-CN,en,*",
            "Accept-Encoding": "br, gzip, deflate",
            "Accept": "application/json",
        }
        default_headers.update(headers or {})
        self.client = httpx.Client(
            base_url=base_url or self.base_url or "",
            headers=default_headers,
            follow_redirects=True,
            http2=True,
            timeout=httpx.Timeout(30, read=30),
            proxy=HttpConfigService.proxy,
            trust_env=False,
        )

    def get_json(self, path, params=None):
        rsp = self._request("GET", path, params=params)
        return rsp.json()

    def get_text(self, path, params=None):
        rsp = self._request("GET", path, params=params)
        return rsp.text

    def post_json(self, path, json=None):
        rsp = self._request("POST", path, json=json)
        return rsp.json()

    def is_available(self, url):
        try:
            rsp = self._request("HEAD", url)
            if rsp.status_code == 405:
                rsp = self._request("GET", url, headers={"Range": "bytes=0-0"})
            return 200 <= rsp.status_code < 400
        except httpx.HTTPError:
            return False

    def _request(self, method, path, **kwargs):
        from mirrors.mirror_manager import MirrorManager

        url = str(path)
        if not url.startswith(("http://", "https://")):
            url = str(self.client.base_url.join(url))
        urls = list(MirrorManager.get_urls([url]))
        last_error = None
        for attempt in range(1, self.try_times + 1):
            request_url = urls[min(len(urls), attempt) - 1]
            try:
                with DnsUtils.resolving(HttpConfigService.proxy is None):
                    rsp = self.client.request(method, request_url, **kwargs)
                rsp.raise_for_status()
                return rsp
            except httpx.HTTPError as ex:
                last_error = ex
                if attempt < len(urls):
                    continue
                if attempt >= self.try_times:
                    if isinstance(ex, httpx.HTTPStatusError):
                        status = ex.response.status_code
                        raise RuntimeError(
                            f"调用接口失败（{status}）：{url} ，请重试几次，或打开代理再试"
                        ) from ex
                    raise RuntimeError(
                        f"调用接口失败：{url} ，请重试几次，或打开代理再试"
                    ) from ex
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"调用接口失败：{path}")

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
