from api.modrinth_api_client import ModrinthApiClient
from storage.local_storage import persistent_storage


class ModrinthService:
    def __init__(self):
        self.modrinth = ModrinthApiClient()

    def fetch_mod_file_url(self, files):
        mods = [file for file in files if getattr(file, "is_mod", False) and file.sha1]
        if not mods:
            return
        storage = persistent_storage()

        def update(cache):
            cache = cache or {"urls": {}}
            urls = cache.setdefault("urls", {})
            request_mods = []
            for file in mods:
                if file.sha1 in urls:
                    url = urls[file.sha1]
                    if url:
                        file.set_downloadable(
                            file.display_name or file.sha1, [url, *file.urls]
                        )
                else:
                    request_mods.append(file)

            if request_mods:
                result = self.modrinth.version_file(
                    [file.sha1 for file in request_mods]
                )
                by_hash = result if isinstance(result, dict) else {}
                for file in list(request_mods):
                    item = by_hash.get(file.sha1)
                    matched_url = self.matched_url(file.sha1, item)
                    if matched_url:
                        file.set_downloadable(
                            file.display_name or file.sha1, [matched_url, *file.urls]
                        )
                        urls[file.sha1] = matched_url
                        request_mods.remove(file)

                for missed in request_mods:
                    urls[missed.sha1] = None
            return cache

        storage.get_or_update_object("modrinth-file", update, "ModrinthCache")

    @staticmethod
    def matched_url(sha1, item):
        if not item:
            return None
        for candidate in item.get("files") or []:
            if candidate.get("hashes", {}).get("sha1") == sha1 and candidate.get("url"):
                return candidate["url"]
        return None

    def close(self):
        self.modrinth.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
