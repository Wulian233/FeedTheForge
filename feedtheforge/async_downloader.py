import aiohttp
import aiofiles

from feedtheforge.const import lang

class AsyncDownloader:
    def __init__(self, retries=3, timeout_enabled=True):
        self.session = None
        self.retries = retries
        self.timeout_enabled = timeout_enabled

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=10) if self.timeout_enabled else None
        self.session = await aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            timeout=timeout
        ).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.__aexit__(exc_type, exc, tb)

    async def download_file(self, url, output_path):
        failure_message_printed = False
        for attempt in range(1, self.retries + 1):
            try:
                async with self.session.get(url) as response:
                    async with aiofiles.open(output_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(1024*64):
                            await f.write(chunk)
                return  # 下载成功，退出函数
            except Exception:
                path_part = output_path.split("overrides")[-1]
                if attempt >= self.retries:
                    if not failure_message_printed:
                        print(lang.t("feedtheforge.async_downloader.skip",
                                      path_part=path_part))
                        failure_message_printed = True
                else:
                    if not failure_message_printed:
                        print(lang.t("feedtheforge.async_downloader.retries")+
                              f"({attempt}/{self.retries})...")
                        failure_message_printed = True 

    async def fetch_json(self, url):
        async with self.session.get(url) as response:
            return await response.json()
