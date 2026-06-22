from api.curseforge_api_client import CurseforgeApiClient


class CurseforgeService:
    @classmethod
    def fetch_mod_info(cls, mod_files):
        file_dict = {file.sha1: file for file in mod_files if file.sha1}
        if not file_dict:
            return
        with CurseforgeApiClient() as api:
            result = api.match_files(file.cf_murmur for file in file_dict.values())
        for matched_file in result.get("exactMatches", []):
            file_info = matched_file.get("file") or {}
            sha1 = next(
                (
                    item.get("value")
                    for item in file_info.get("hashes", [])
                    if item.get("algo") == 1
                ),
                None,
            )
            if sha1 is not None and sha1 in file_dict:
                file_dict[sha1].with_curseforge_info(
                    file_info.get("modId"), file_info.get("id")
                )
