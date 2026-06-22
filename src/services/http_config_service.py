import os
from urllib.request import getproxies

from app_info import NAME, VERSION
from global_style import console


class HttpConfigService:
    proxy = None
    user_agent = f"{NAME}/{VERSION}"
    thread = 8
    curseforge_key = "$2a$10$KauzeIBqTRY2jwkx64A.Cep7cmWFGGYVncpqvfOCOee/90YPgkgfy"

    @classmethod
    def setup_download_http(cls, options):
        if options.thread is not None:
            cls.thread = int(options.thread)
        if options.curseforge_key is not None:
            cls.curseforge_key = options.curseforge_key
        cls.setup_http(options)

    @classmethod
    def setup_http(
        cls,
        options=None,
        thread=None,
        proxy=None,
        user_agent=None,
        curse_key=None,
        no_proxy=False,
    ):
        if options is not None:
            user_agent = options.user_agent
            proxy = options.proxy
            no_proxy = options.no_proxy
            thread = getattr(options, "thread", None)
            curse_key = getattr(options, "curseforge_key", None)
        if thread is not None:
            cls.thread = int(thread)
        if curse_key is not None:
            cls.curseforge_key = curse_key
        if user_agent is not None:
            cls.user_agent = user_agent
        cls.setup_http_proxy(no_proxy, proxy)

    @classmethod
    def setup_http_proxy(cls, no_proxy, proxy_uri):
        if no_proxy:
            cls.proxy = None
            return

        if proxy_uri is not None:
            cls.proxy = proxy_uri
            console.print("（正在使用命令行指定的代理）", style="blue")
            console.print()
            return

        proxies = getproxies()
        proxy_uri = proxies.get("https") or proxies.get("http")
        if proxy_uri is not None:
            cls.proxy = proxy_uri
            console.print("（正在使用系统代理）", style="blue")
            console.print()
            return

        proxy_uri = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        if proxy_uri is not None:
            cls.proxy = proxy_uri
            console.print("（正在使用环境变量指定的代理）", style="blue")
            console.print()
