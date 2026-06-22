from api.base_api_client import BaseApiClient


class MojangApiClient(BaseApiClient):
    base_url = "https://piston-meta.mojang.com/"

    def get_game_versions(self):
        return self.get_json("mc/game/version_manifest.json")

    def get_game_manifest(self, url):
        rsp = self.client.get(url)
        rsp.raise_for_status()
        return rsp.json()
