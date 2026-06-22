from api.base_api_client import BaseApiClient


class FabricApiClient(BaseApiClient):
    base_url = "https://meta.fabricmc.net/v2/"

    def get_loader_versions(self, game_version):
        return self.get_json(f"versions/loader/{game_version}")

    def get_installer_meta(self):
        return self.get_json("versions/installer")

    def get_server_loader_url(self, game_version, loader_version, installer_version):
        rsp = self.client.get(
            f"versions/loader/{game_version}/{loader_version}/{installer_version}/server/jar"
        )
        if rsp.status_code == 404:
            return None
        rsp.raise_for_status()
        return str(rsp.url)

    def get_server_manifest(self, game_version, loader_version):
        return self.get_json(
            f"versions/loader/{game_version}/{loader_version}/server/json"
        )
