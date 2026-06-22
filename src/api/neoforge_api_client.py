from api.base_api_client import BaseApiClient


class NeoForgeApiClient(BaseApiClient):
    base_url = "https://maven.neoforged.net/releases/"

    def maven_metadata(self, artifact):
        path = artifact.replace(".", "/")
        return self.get_text(f"{path}/maven-metadata.xml")

    def get_server_installer_url(self, game_version, neoforge_version):
        if game_version == "1.20.1":
            url = f"https://maven.neoforged.net/net/neoforged/forge/1.20.1-{neoforge_version}/forge-1.20.1-{neoforge_version}-installer.jar"
            url2 = f"https://maven.neoforged.net/releases/net/neoforged/forge/1.20.1-{neoforge_version}/forge-1.20.1-{neoforge_version}-installer.jar"
        else:
            url = f"https://maven.neoforged.net/net/neoforged/neoforge/{neoforge_version}/neoforge-{neoforge_version}-installer.jar"
            url2 = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{neoforge_version}/neoforge-{neoforge_version}-installer.jar"
        return [url, url2] if self.is_available(url2) else []
