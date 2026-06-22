from storage.file_entry import FileEntry
from storage.repo_type import RepoType


class FileSide:
    CLIENT = 1
    SERVER = 2
    BOTH = CLIENT | SERVER


class FTBFileEntry(FileEntry):
    def __init__(self, file):
        hashes = file.get("hashes") or {}
        sha1 = (hashes.get("sha1") or "").lower()
        super().__init__(RepoType.ASSET_V2, self._asset_cache_path(sha1))
        self.cf_murmur = hashes.get("cfMurmur") or hashes.get("cf_murmur") or 0
        self.is_mod = str(file.get("type") or "").lower() == "mod"
        self.sha512 = hashes.get("sha512")
        if file.get("serveronly"):
            self.side = FileSide.SERVER
        elif file.get("clientonly"):
            self.side = FileSide.CLIENT
        else:
            self.side = FileSide.BOTH
        self.optional = bool(file.get("optional"))
        self.curseforge = None

        self.with_sha1(sha1)
        self.with_size(file.get("size"))
        self.with_archive_entry_name(file.get("path"), file.get("name"))
        if (
            self.archive_entry_name
            and self.archive_entry_name.lower().startswith("mods/")
            and self.archive_entry_name.lower().endswith(".jar.disabled")
        ):
            self.archive_entry_name = self.archive_entry_name[:-9]

        urls = [file.get("url"), *(file.get("mirrors") or [])]
        self.set_downloadable(file.get("name") or self.archive_entry_name or sha1, urls)

    def with_curseforge_info(self, project_id, file_id):
        self.curseforge = {"project_id": project_id, "file_id": file_id}
        return self

    @staticmethod
    def _asset_cache_path(sha1):
        sha1 = sha1.lower()
        if len(sha1) < 2:
            return ["unknown", sha1 or "file"]
        return [sha1[:2], sha1[2:]]
