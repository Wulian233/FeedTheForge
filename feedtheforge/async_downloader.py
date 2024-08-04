import aiohttp
import aiofiles
import asyncio

class AsyncDownloader:
    def __init__(self, retries=2, retry_delay=2):
        self.session = None
        self.retries = retries
        self.retry_delay = retry_delay

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=10)  # 设置总超时
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
                print(f"文件下载成功: {output_path}")
                break  # 下载成功，退出循环
            except Exception:
                attempts += 1
                if attempts >= self.retries:
                    print(f"文件下载失败，跳过: {output_path}")
                else:
                    print(f"下载失败，尝试重新下载 ({attempts}/{self.retries})...")
                    await asyncio.sleep(self.retry_delay)

    async def fetch_json(self, url):
        async with self.session.get(url) as response:
            return await response.json()
