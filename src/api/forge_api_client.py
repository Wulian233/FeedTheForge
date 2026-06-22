from api.base_api_client import BaseApiClient


class ForgeApiClient(BaseApiClient):
    base_url = "https://maven.minecraftforge.net/"

    def maven_metadata(self, artifact):
        path = artifact.replace(".", "/")
        return self.get_text(f"{path}/maven-metadata.xml")

    def get_server_installer_url(self, game_version, forge_version):
        url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{game_version}-{forge_version}/forge-{game_version}-{forge_version}-installer.jar"
        if self.is_available(url):
            return url

        # forge你在干什么？
        url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{game_version}-{forge_version}-{game_version}/forge-{game_version}-{forge_version}-{game_version}-installer.jar"
        if self.is_available(url):
            return url
        return None
