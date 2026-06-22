from api.base_api_client import BaseApiClient
from services.http_config_service import HttpConfigService


class CurseforgeApiClient(BaseApiClient):
    base_url = "https://api.curseforge.com/v1/"

    # noinspection PyMethodMayBeStatic
    def __init__(self):
        headers = {}
        if HttpConfigService.curseforge_key:
            headers["x-api-key"] = HttpConfigService.curseforge_key
        super().__init__(headers=headers)

    def get_mod_file(self, mod_id, file_id):
        return self.get_json(f"mods/{mod_id}/files/{file_id}")

    def get_files(self, file_ids):
        return self.post_json("mods/files", json={"fileIds": list(file_ids)}).get(
            "data", []
        )

    def match_files(self, fingerprints):
        return self.post_json(
            "fingerprints/432", json={"fingerprints": list(fingerprints)}
        ).get("data", {})
