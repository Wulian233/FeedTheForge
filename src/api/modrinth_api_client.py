from api.base_api_client import BaseApiClient


class ModrinthApiClient(BaseApiClient):
    base_url = "https://api.modrinth.com/"

    def version_file(self, hashes, algorithm="sha1"):
        return self.post_json(
            "v2/version_files", json={"hashes": hashes, "algorithm": algorithm}
        )

    def version_file_update(self, hashes, algorithm="sha1"):
        return self.post_json(
            "v2/version_files/update", json={"hashes": hashes, "algorithm": algorithm}
        )
