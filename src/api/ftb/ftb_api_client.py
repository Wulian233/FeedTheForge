from api.base_api_client import BaseApiClient
from api.ftb.ftb_exception import FTBException


class FTBApiClient(BaseApiClient):
    base_url = "https://api.feed-the-beast.com/v1/modpacks/public/"

    def _call(self, path, params=None):
        data = self.get_json(path, params=params)
        if (
            isinstance(data, dict)
            and data.get("status")
            and data.get("status") != "success"
        ):
            raise FTBException(path, data.get("status"), data.get("message"))
        return data

    def search(self, keyword):
        return self._call(
            "modpack/search/20/detailed",
            params={"platform": "modpacksch", "term": keyword},
        )

    def get_list(self):
        return self._call("modpack/all")

    def get_featured(self):
        return self._call("modpack/featured/20")

    def get_info(self, modpack_id):
        return self._call(f"modpack/{modpack_id}")

    def get_manifest(self, modpack_id, version_id):
        return self._call(f"modpack/{modpack_id}/{version_id}")

    def get_mod_info(self, sha1):
        return self._call(f"mod/{sha1}")
