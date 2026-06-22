import json
import os
from zipfile import ZIP_DEFLATED, ZipFile

from global_style import success
from services.file_download_service import FileDownloadService
from services.model.ftb_file_entry import FileSide
from services.modrinth_service import ModrinthService
from services.server_mod_loader_service import ServerModLoaderService
from utils.path_utils import escape_file_name

UNIX_EXECUTABLE_ATTR = -2115174400


class ServerModpackProcessor:
    def __init__(self, pack, preinstall):
        self.modpack = pack
        self.preinstall = preinstall
        self.name = f"{pack.name} v{pack.version.name} Server{' Preinstalled' if preinstall else ''}"
        self.assets = [file for file in pack.files if file.side & FileSide.SERVER]
        self.modloader = None
        self.mod_loader_files = None

    @property
    def default_file_name(self):
        return f"{escape_file_name(self.modpack.name)} v{self.modpack.version.name} Server{' Preinstalled' if self.preinstall else ''}.zip"

    def download(self):
        download_task = [asset for asset in self.assets if not asset.validate()]
        with ModrinthService() as modrinth:
            modrinth.fetch_mod_file_url([file for file in download_task if file.is_mod])
        FileDownloadService.download("下载整合包文件", download_task, False)
        if self.modpack.icon:
            FileDownloadService.download("下载图标", [self.modpack.icon], True)
        success("√ 下载完成")

    def process(self):
        self.modloader = ServerModLoaderService(self.modpack, self.preinstall)
        self.mod_loader_files = self.modloader.get_mod_loader_files()
        success("√ 服务端预安装完成")

    def pack(self, stream, dst_hint):
        with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
            self._write_assets(archive)
            self._write_manifest(archive)
            self._set_comment(archive)
            self._write_readme_md(archive)
            self._write_icon(archive)
            self._write_loader_files(archive)
        success(f"√ 打包完成：{dst_hint}")

    def _write_manifest(self, archive):
        # 瞎编的清单格式
        archive.writestr(
            "server-manifest.json",
            json.dumps(
                {
                    "name": self.modpack.name,
                    "version": self.modpack.version.name,
                    "gameVersion": self.modpack.runtime.game_version,
                    "modLoaderType": self.modpack.runtime.mod_loader_type,
                    "modLoaderVersion": self.modpack.runtime.mod_loader_version,
                    "javaVersion": self.modpack.runtime.java_version,
                    "recommendedRam": self.modpack.runtime.recommended_ram,
                    "minimumRam": self.modpack.runtime.minimum_ram,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

    def _write_assets(self, archive):
        for file in self.assets:
            self._write_file(archive, self.name, file)

    def _set_comment(self, archive):
        lines = [self.name]
        if self.modpack.summary:
            lines.extend(["", self.modpack.summary])
        lines.extend(["", self.modpack.home_page_url])
        archive.comment = "\n".join(lines).encode("utf-8")

    def _write_readme_md(self, archive):
        if self.modpack.readme:
            archive.writestr("README.md", self.modpack.readme)

    def _write_icon(self, archive):
        if self.modpack.icon and not self.modpack.icon.unreachable:
            self._write_file(archive, None, self.modpack.icon)

    def _write_loader_files(self, archive):
        if not self.mod_loader_files:
            return
        for file in self.mod_loader_files:
            self._write_file(archive, self.name, file)
        if os.name == "nt" and self.preinstall:
            archive.writestr("双击“run.bat”文件即可启动服务端", "")

    @staticmethod
    def _write_file(archive, prefix, file):
        name = "/".join(part for part in (prefix, file.archive_entry_name) if part)
        archive.write(file.local_path, name)
        entry = archive.getinfo(name)
        if file.unix_executable:
            entry.external_attr = UNIX_EXECUTABLE_ATTR
