import json
import os
import re
import shutil
import zipfile
from pathlib import Path

from api.neoforge_api_client import NeoForgeApiClient
from server_installer.abstract_mod_server_installer import \
    AbstractModServerInstaller
from server_installer.maven_file_entry import MavenFileEntry
from storage.file_entry import FileEntry
from storage.local_storage import LocalStorage
from storage.repo_type import RepoType
from utils.jar_launcher_utils import inject_forge_script


class NeoForgeServerInstaller(AbstractModServerInstaller):
    min_game_version = "1.20.1"

    def __init__(self):
        super().__init__()
        self.installer = None
        self.server_jar_path = None
        self.libraries = []
        self.mappings = None
        self.temp_storage = LocalStorage.get_temp_storage("neoforge-install")

    def resolve_standalone_loader_jar(self):
        installer_file_name = (
            f"neoforge-installer-{self.game_version}-{self.loader_version}.jar"
        )
        file = FileEntry(
            RepoType.MOD_LOADER_JAR, installer_file_name
        ).with_archive_entry_name(installer_file_name)
        if file.validate():
            return [file]
        with NeoForgeApiClient() as api:
            urls = api.get_server_installer_url(self.game_version, self.loader_version)
        if not urls:
            return []
        file.set_downloadable(installer_file_name, urls)
        return [file]

    def is_preinstallation_supported(self):
        return _version_tuple(self.game_version) >= _version_tuple(
            self.min_game_version
        )

    def resolve_installer(self):
        installers = self.resolve_standalone_loader_jar()
        if not installers:
            raise RuntimeError(
                f"无法获取 neoforge-{self.game_version}-{self.loader_version} 安装器下载链接"
            )
        self.installer = installers[0]
        return installers

    def resolve_installer_dependencies(self, manifest):
        assert self.installer is not None
        with zipfile.ZipFile(self.installer.local_path) as archive:
            installer_json = _json_in_zip(
                archive,
                "install_profile.json",
                f"不支持 neoforge-{self.game_version}-{self.loader_version} 服务端预安装",
            )
            version_json = _json_in_zip(
                archive,
                str(installer_json["json"]).lstrip("./"),
                f"不支持 neoforge-{self.game_version}-{self.loader_version} 服务端预安装",
            )

        if installer_json.get("spec") != 1:
            raise RuntimeError(
                f"不支持 neoforge-{self.game_version}-{self.loader_version} 服务端预安装"
            )

        self.server_jar_path = Path(
            installer_json["serverJarPath"]
            .replace("{LIBRARY_DIR}", "libraries")
            .replace("{MINECRAFT_VERSION}", self.game_version)
            .lstrip("./")
        )

        libs = []
        for doc in (installer_json, version_json):
            for lib in doc.get("libraries", []):
                artifact = lib.get("downloads", {}).get("artifact", {})
                maven_lib = _get_maven_lib(
                    lib["name"], artifact.get("path"), artifact.get("url")
                )
                if maven_lib:
                    libs.append(maven_lib)
        self.libraries = _distinct_by_artifact(libs)

        server_mappings = manifest.get("downloads", {}).get("server_mappings")
        if not server_mappings:
            return self.libraries
        self.mappings = (
            FileEntry(RepoType.SERVER_MAPPINGS, self.game_version)
            .set_downloadable("server_mappings.txt", [server_mappings.get("url")])
            .with_size(server_mappings.get("size"))
            .with_sha1(server_mappings.get("sha1"))
        )
        return [*self.libraries, self.mappings]

    def preinstall(self, java, server_jar):
        assert self.installer is not None
        assert self.server_jar_path is not None
        # 复制服务端本体
        server_jar_path = Path(self.temp_storage.work_space) / self.server_jar_path
        server_jar_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(server_jar.local_path, server_jar_path)

        # 复制依赖
        for lib in self.libraries:
            lib_jar_path = (
                Path(self.temp_storage.work_space)
                / "libraries"
                / lib.artifact.file_path
            )
            lib_jar_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(lib.local_path, lib_jar_path)

        # 执行安装
        fat_installer_path = (
            self.installer.local_path
            if self.mappings is None
            else self._generate_fat_installer()
        )
        ret = java.execute_jar(
            fat_installer_path,
            ["--installServer", ".", "--offline"],
            self.temp_storage.work_space,
        )
        if ret != 0:
            raise RuntimeError(
                f"neoforge-{self.game_version}-{self.loader_version} 服务端预安装失败 "
            )
        if fat_installer_path != self.installer.local_path:
            Path(fat_installer_path).unlink(missing_ok=True)

        title = (
            self.server_name
            or f"NeoForge Server {self.game_version} {self.loader_version}"
        )
        files = []
        launcher_script_name = inject_forge_script(
            self.temp_storage.work_space, java.dist_name, title, self.ram
        )
        if launcher_script_name:
            files.extend(java.get_jre_files())

        # 生成EULA同意文件
        self.generate_eula_agreement_file(self.temp_storage.work_space)

        files.extend(self.temp_storage.get_workspace_files())
        if launcher_script_name and os.name != "nt":
            for file in files:
                if file.archive_entry_name == launcher_script_name:
                    file.set_unix_executable()
        return files

    def _generate_fat_installer(self):
        assert self.installer is not None
        assert self.mappings is not None
        path = Path(self.temp_storage.work_space) / "installer.jar"
        with zipfile.ZipFile(self.installer.local_path) as src_zip:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as dst_zip:
                for entry in src_zip.infolist():
                    if entry.filename.startswith(
                        "META-INF"
                    ) and entry.filename.endswith((".SF", ".RSA")):
                        continue
                    dst_zip.writestr(entry, src_zip.read(entry))
                dst_zip.writestr(
                    f"maven/minecraft/{self.game_version}/server_mappings.txt",
                    Path(self.mappings.local_path).read_bytes(),
                )
        return path

    def close(self):
        self.temp_storage.dispose()


def _get_maven_lib(artifact_id, path, provided_url):
    if not provided_url:
        return None
    maven_file = MavenFileEntry(artifact_id).with_maven_base_archive_entry_name()
    release_url_prefix = "//maven.neoforged.net/releases/"
    if release_url_prefix in provided_url:
        maven_file.with_maven_url(
            provided_url.replace(release_url_prefix, "//maven.neoforged.net/"),
            provided_url,
        )
    else:
        maven_file.with_maven_url(provided_url)
    if path:
        maven_file.with_archive_entry_name("libraries", path)
    return maven_file


def _json_in_zip(archive, entry_name, error_message):
    try:
        return json.loads(archive.read(entry_name).decode("utf-8"))
    except KeyError as ex:
        raise RuntimeError(error_message) from ex


def _distinct_by_artifact(libs):
    result = {}
    for lib in libs:
        result.setdefault(lib.artifact.id, lib)
    return list(result.values())


def _version_tuple(value):
    numbers = re.findall(r"\d+", str(value))
    return tuple(int(number) for number in numbers[:3])
