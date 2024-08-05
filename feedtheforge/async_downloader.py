import aiohttp
import aiofiles

class AsyncDownloader:
    def __init__(self, retries=2, timeout_enabled=True):
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
        attempts = 0
        while attempts < self.retries:
            try:
                async with self.session.get(url) as response:
                    async with aiofiles.open(output_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(1024*64):
                            await f.write(chunk)
                break
            except Exception:
                attempts += 1
                path_part = output_path.split("overrides")[-1]
                if attempts >= self.retries:
                    if not failure_message_printed:
                        print(f"文件下载失败，跳过: {path_part}")
                        failure_message_printed = True
                else:
                    if not failure_message_printed:
                        print(f"下载失败，尝试重新下载 ({attempts}/{self.retries})...")
                        failure_message_printed = True

    async def fetch_json(self, url):
        async with self.session.get(url) as response:
            return await response.json()
