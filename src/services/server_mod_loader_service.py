import os
import platform
import zipfile
from contextlib import suppress
from pathlib import Path

from api.azul_api_client import AzulApiClient
from api.mojang_api_client import MojangApiClient
from server_installer.fabric_server_installer import FabricServerInstaller
from server_installer.forge_server_installer import ForgeServerInstaller
from server_installer.java_runtime import JavaRuntime
from server_installer.neoforge_server_installer import NeoForgeServerInstaller
from services.file_download_service import FileDownloadService
from storage.file_entry import FileEntry
from storage.local_storage import persistent_storage
from storage.repo_type import RepoType


class ServerModLoaderService:
    # 此版本的8在绝大多数情况下不会有问题
    default_java8_version = "8u312"

    def __init__(self, pack, preinstall):
        self.pack = pack
        self.preinstall = preinstall
        self.installer = self.get_installer()
        self.preinstall_supported = (
            self.installer.is_preinstallation_supported() if self.installer else False
        )
        self.java = None

    def get_mod_loader_files(self):
        # 不预安装，只带一个jar
        if not self.preinstall:
            return self.get_standalone_loader_jar()

        if not self.preinstall_supported or not self.installer:
            raise RuntimeError(
                f"不支持预安装 {self.pack.runtime.mod_loader_type}-{self.pack.runtime.game_version}-{self.pack.runtime.mod_loader_version} 服务端"
            )

        self.java = self.get_java_runtime()
        manifest = self.get_game_manifest()
        server_jar = self.get_server_jar(manifest)
        loader_files = self.get_mod_loader_files_with_java(
            self.java, manifest, server_jar
        )
        return loader_files

    def get_standalone_loader_jar(self):
        if self.installer:
            with suppress(Exception):
                installer_jar = self.installer.resolve_standalone_loader_jar()
                if installer_jar:
                    FileDownloadService.download(
                        f"下载 {self.pack.runtime.mod_loader_type} 加载器",
                        installer_jar,
                        True,
                    )
                    return installer_jar
        # 不支持、获取失败、下载失败就不带了，自己下载去
        return []

    def get_mod_loader_files_with_java(self, java, manifest, server_jar):
        installer = self.installer
        if installer is None:
            raise RuntimeError(
                f"不支持预安装 {self.pack.runtime.mod_loader_type}-{self.pack.runtime.game_version}-{self.pack.runtime.mod_loader_version} 服务端"
            )

        installer_jar = installer.resolve_installer()
        if installer_jar:
            FileDownloadService.download(
                f"下载 {self.pack.runtime.mod_loader_type} 安装器", installer_jar, True
            )

        deps = installer.resolve_installer_dependencies(manifest)
        if deps:
            FileDownloadService.download(
                f"下载 {self.pack.runtime.mod_loader_type} 依赖", deps, True
            )

        return installer.preinstall(java, server_jar)

    def get_installer(self):
        loader_type = self.pack.runtime.mod_loader_type.lower()
        if loader_type == "forge":
            installer = ForgeServerInstaller()
        elif loader_type == "fabric":
            installer = FabricServerInstaller()
        elif loader_type == "neoforge":
            installer = NeoForgeServerInstaller()
        else:
            return None
        installer.game_version = self.pack.runtime.game_version
        installer.loader_version = self.pack.runtime.mod_loader_version
        installer.server_name = f"{self.pack.name} v{self.pack.version.name} Server"
        installer.ram = self.pack.runtime.recommended_ram
        return installer

    def get_game_manifest(self):
        storage = persistent_storage()
        cached = storage.get_object(
            f"game-{self.pack.runtime.game_version}", "GameManifest"
        )
        if cached:
            return cached
        with MojangApiClient() as api:
            versions = api.get_game_versions()
            version = next(
                (
                    item
                    for item in versions.get("versions", [])
                    if item.get("id") == self.pack.runtime.game_version
                ),
                None,
            )
            if not version:
                raise RuntimeError("未知的 MC 版本：" + self.pack.runtime.game_version)
            manifest = api.get_game_manifest(version["url"])
        storage.save_object(
            f"game-{self.pack.runtime.game_version}", manifest, "GameManifest"
        )
        return manifest

    def get_server_jar(self, manifest):
        info = manifest.get("downloads", {}).get("server")
        if not info:
            raise RuntimeError("当前 MC 版本没有服务端下载信息")
        server_jar = FileEntry(
            RepoType.SERVER_JAR, f"{self.pack.runtime.game_version}.jar"
        ).set_sha1_file_required()
        if server_jar.validate(False):
            return server_jar
        server_jar.set_downloadable(
            f"mc-server-{self.pack.runtime.game_version}.jar", [info.get("url")]
        ).with_sha1(info.get("sha1")).with_size(info.get("size"))
        FileDownloadService.download("下载服务端", [server_jar], True)
        return server_jar

    def get_java_runtime(self):
        java_archive_file = self.get_java_runtime_archive()
        FileDownloadService.download("下载 Java 运行环境", [java_archive_file], True)
        return JavaRuntime.from_archive(java_archive_file.local_path)

    def get_java_runtime_archive(self):
        os_name = _azul_os()
        arch = _azul_arch()
        archive_type = "zip" if os.name == "nt" else "tar.gz"
        java_version = str(self.pack.runtime.java_version)
        display_file_name = f"zulu-{java_version}-{os_name}.{archive_type}"

        # 兼容旧版索引
        java_archive_file = FileEntry(RepoType.JRE_ARCHIVE, display_file_name)
        if java_archive_file.validate():
            # 检查之前误下载的musl版JRE
            if _is_musl_jre(java_archive_file.local_path):
                java_archive_file.delete()
            else:
                return java_archive_file

        major = java_version.split(".", 1)[0]
        if major == "1" and "." in java_version:
            parts = java_version.split(".")
            major = parts[1]
        base = ".".join(_version_numbers(java_version)[:3]) or major
        version_pairs = [(base, "jre"), (base, "jdk")]
        if major == "8":
            version_pairs.extend(
                [
                    (self.default_java8_version, "jre"),
                    (self.default_java8_version, "jdk"),
                ]
            )
        version_pairs.extend([(major, "jre"), (major, "jdk")])

        with AzulApiClient() as api:
            package = None
            for version, package_type in version_pairs:
                packages = api.packages(
                    version, os_name, arch, archive_type, package_type
                )
                package = next(
                    (
                        item
                        for item in packages
                        if "musl" not in item.get("name", "").lower()
                        and str(item.get("java_version", [major])[0]) == str(major)
                    ),
                    None,
                )
                if package:
                    break
        if not package:
            raise RuntimeError(
                f"服务端预安装失败：无法获取 Java{self.pack.runtime.java_version} 运行环境信息"
            )

        # 新版索引
        return FileEntry(RepoType.JRE_ARCHIVE, package["name"]).set_downloadable(
            display_file_name, [package["download_url"]]
        )

    def close(self):
        if self.installer:
            self.installer.close()
        if self.java:
            self.java.close()


def _azul_os():
    if os.name == "nt":
        return "windows"
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    raise RuntimeError("服务端预安装失败：不支持当前操作系统")


def _azul_arch():
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        return "x64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    return machine


def _version_numbers(value):
    result = []
    current = ""
    for char in str(value):
        if char.isdigit():
            current += char
        elif current:
            result.append(current)
            current = ""
    if current:
        result.append(current)
    return result


def _is_musl_jre(archive_path):
    if (
        not str(archive_path).lower().endswith(".zip")
        or not Path(archive_path).exists()
    ):
        return False
    with suppress(OSError, zipfile.BadZipFile, IndexError):
        with zipfile.ZipFile(archive_path) as archive:
            first = archive.infolist()[0].filename
            return "musl" in first
    return False
