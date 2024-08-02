import aiohttp

class AsyncDownloader:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = await aiohttp.ClientSession().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.__aexit__(exc_type, exc, tb)

    async def download_file(self, url, output_path):
        async with self.session.get(url) as response:
            with open(output_path, "wb") as f:
                while chunk := await response.content.read(1024):
                    f.write(chunk)

    async def fetch_json(self, url):
        async with self.session.get(url) as response:
            return await response.json()