import json
from zipfile import ZIP_DEFLATED, ZipFile

from rich.console import Console

from global_style import success
from services.file_download_service import FileDownloadService
from services.model.ftb_file_entry import FileSide
from services.modrinth_service import ModrinthService
from utils.path_utils import escape_file_name

console = Console()
UNIX_EXECUTABLE_ATTR = -2115174400


class ModrinthModpackProcessor:
    def __init__(self, pack, with_asset):
        self.modpack = pack
        self.with_asset = with_asset
        if with_asset:
            self.offline_assets = [file for file in pack.files if not file.is_mod]
            self.online_assets = [file for file in pack.files if file.is_mod]
        else:
            self.offline_assets = []
            self.online_assets = pack.files

    @property
    def default_file_name(self):
        suffix = "" if self.with_asset else " Light"
        return f"{escape_file_name(self.modpack.name)} v{self.modpack.version.name}{suffix}.zip"

    def download(self):
        with console.status("[yellow bold]检查缓存[/yellow bold]"):
            download_task = [
                asset for asset in self.offline_assets if not asset.validate()
            ]
        with ModrinthService() as modrinth:
            modrinth.fetch_mod_file_url(
                [file for file in [*self.online_assets, *download_task] if file.is_mod]
            )
        FileDownloadService.download("下载整合包文件", download_task, False)
        if self.modpack.icon:
            FileDownloadService.download("下载图标", [self.modpack.icon], True)
        success("√ 下载完成")

    @staticmethod
    def process():
        return None

    def pack(self, stream, dst_hint):
        with console.status("[yellow bold]打包中[/yellow bold]"):
            with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
                self._write_assets(archive)
                self._write_manifest(archive)
                self._set_comment(archive)
                self._write_readme_md(archive)
                self._write_icon(archive)
        success(f"√ 打包完成：{dst_hint}")

    def _write_manifest(self, archive):
        loader_key = self._loader_key()
        game_version = self.modpack.runtime.game_version
        loader_version = self.modpack.runtime.mod_loader_version
        if not game_version:
            raise RuntimeError("Game version not set")
        if not loader_key or not loader_version:
            raise RuntimeError("Mod loader not set")
        dependencies = {
            "minecraft": game_version,
            loader_key: loader_version,
        }
        files = []
        for file in self.online_assets:
            if not file.archive_entry_name:
                raise RuntimeError("Archive entry name not set")
            if not file.sha1:
                raise RuntimeError("Sha1 not set")
            if file.size is None:
                raise RuntimeError("File size not set")
            if not file.urls:
                raise RuntimeError("File url not set")
            files.append(
                {
                    "path": file.archive_entry_name,
                    "hashes": {"sha1": file.sha1, "sha512": file.sha512},
                    "env": {
                        "client": self._env(file, FileSide.CLIENT),
                        "server": self._env(file, FileSide.SERVER),
                    },
                    "fileSize": file.size,
                    "downloads": file.urls,
                }
            )
        manifest = {
            "formatVersion": 1,
            "game": "minecraft",
            "name": self.modpack.name,
            "summary": self.modpack.summary,
            "versionId": self.modpack.version.name,
            "dependencies": dependencies,
            "files": files,
        }
        archive.writestr(
            "modrinth.index.json", json.dumps(manifest, ensure_ascii=False, indent=2)
        )

    def _write_assets(self, archive):
        for file in self.offline_assets:
            if file.side == FileSide.BOTH:
                prefix = "overrides"
            elif file.side == FileSide.SERVER:
                prefix = "server-overrides"
            else:
                prefix = "client-overrides"
            self._write_file(archive, prefix, file)

    def _set_comment(self, archive):
        lines = [f"{self.modpack.name} v{self.modpack.version.name}"]
        if self.modpack.summary:
            lines.extend(["", self.modpack.summary])
        lines.extend(["", self.modpack.home_page_url])
        archive.comment = "\n".join(lines).encode("utf-8")

    def _write_readme_md(self, archive):
        if self.modpack.readme and self.modpack.readme.strip():
            archive.writestr("overrides/README.md", self.modpack.readme)

    def _write_icon(self, archive):
        if self.modpack.icon and not self.modpack.icon.unreachable:
            self._write_file(archive, "overrides", self.modpack.icon)

    @staticmethod
    def _write_file(archive, prefix, file):
        if not file.archive_entry_name:
            raise RuntimeError(
                f'文件"{file.display_name or file.local_path}"未设置EntryName'
            )
        name = "/".join(part for part in (prefix, file.archive_entry_name) if part)
        archive.write(file.local_path, name)
        entry = archive.getinfo(name)
        if file.unix_executable:
            entry.external_attr = UNIX_EXECUTABLE_ATTR

    def _loader_key(self):
        if self.modpack.runtime.mod_loader_type == "fabric":
            return "fabric-loader"
        if self.modpack.runtime.mod_loader_type == "quilt":
            return "quilt-loader"
        return self.modpack.runtime.mod_loader_type

    @staticmethod
    def _env(file, side):
        if not file.side & side:
            return "unsupported"
        return "optional" if file.optional else "required"
