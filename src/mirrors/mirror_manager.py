from mirrors.bmcl_mirror import BmclMirror
from mirrors.lss233_mirror import Lss233Mirror
from services.http_config_service import HttpConfigService


class MirrorManager:
    mirrors = [BmclMirror(), Lss233Mirror()]

    @classmethod
    def get_urls(cls, urls):
        urls = list(urls)
        seen = set()
        mirrors = [
            mirror
            for mirror in cls.mirrors
            if HttpConfigService.proxy is None or not mirror.cn
        ]
        for url in urls:
            for mirror in mirrors:
                for mirrored in mirror.get_mirrors(url):
                    if mirrored and mirrored not in seen:
                        seen.add(mirrored)
                        yield mirrored
        for url in urls:
            text = str(url)
            if text and text not in seen:
                seen.add(text)
                yield text

    @staticmethod
    def wrap_web_proxy(proxy):
        return proxy
