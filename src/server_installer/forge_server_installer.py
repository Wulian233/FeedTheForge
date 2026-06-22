import json
import os
import re
import shutil
import zipfile
from pathlib import Path

from api.forge_api_client import ForgeApiClient
from server_installer.abstract_mod_server_installer import \
    AbstractModServerInstaller
from server_installer.maven_artifact import MavenArtifact
from server_installer.maven_file_entry import MavenFileEntry
from storage.file_entry import FileEntry
from storage.local_storage import LocalStorage
from storage.repo_type import RepoType
from utils.jar_launcher_utils import generate_script, inject_forge_script


class ForgeServerInstaller(AbstractModServerInstaller):
    min_game_version = "1.6.1"

    def __init__(self):
        super().__init__()
        self.installer = None
        self.installer_spec = -1
        self.server_jar_path = None
        self.loader_file_name = None
        self.libraries = []
        self.mappings = None
        self.temp_storage = LocalStorage.get_temp_storage("forge-install")

    def resolve_standalone_loader_jar(self):
        installer_file_name = (
            f"forge-installer-{self.game_version}-{self.loader_version}.jar"
        )
        file = FileEntry(
            RepoType.MOD_LOADER_JAR, installer_file_name
        ).with_archive_entry_name(installer_file_name)
        if file.validate():
            return [file]
        with ForgeApiClient() as api:
            url = api.get_server_installer_url(self.game_version, self.loader_version)
        if url is None:
            return []
        file.set_downloadable(installer_file_name, [url])
        return [file]

    def is_preinstallation_supported(self):
        return _version_tuple(self.game_version) >= _version_tuple(
            self.min_game_version
        )

    def resolve_installer(self):
        installers = self.resolve_standalone_loader_jar()
        if not installers:
            raise RuntimeError(
                f"无法获取 forge-{self.game_version}-{self.loader_version} 安装器下载链接"
            )
        self.installer = installers[0]
        return installers

    def resolve_installer_dependencies(self, manifest):
        assert self.installer is not None
        with zipfile.ZipFile(self.installer.local_path) as archive:
            installer_json = _json_in_zip(
                archive,
                "install_profile.json",
                f"不支持 forge-{self.game_version}-{self.loader_version} 服务端预安装",
            )
            self.installer_spec = int(installer_json.get("spec", -1))

            # 超低版本特殊处理
            if self.installer_spec == -1:
                self.server_jar_path = f"minecraft_server.{self.game_version}.jar"
                self.loader_file_name = installer_json["install"]["filePath"]
                libs = [
                    MavenFileEntry(lib["name"])
                    .with_maven_repo(
                        _replace_legacy_maven_url(lib.get("url"))
                        or "https://libraries.minecraft.net"
                    )
                    .with_maven_base_archive_entry_name()
                    for lib in installer_json["versionInfo"]["libraries"]
                    if lib.get("serverreq")
                ]
                opts = [
                    MavenFileEntry(lib["artifact"])
                    .with_maven_repo(
                        _replace_legacy_maven_url(lib.get("maven"))
                        or "https://libraries.minecraft.net"
                    )
                    .with_maven_base_archive_entry_name()
                    for lib in installer_json.get("optionals", [])
                    if lib.get("server")
                ]
                self.libraries = [*libs, *opts]
                return self.libraries

            version_json = _json_in_zip(
                archive,
                str(installer_json["json"]).lstrip("./"),
                f"不支持 forge-{self.game_version}-{self.loader_version} 服务端预安装",
            )

        # ( ,1.16.5]
        if self.installer_spec == 0:
            self.server_jar_path = f"minecraft_server.{self.game_version}.jar"
            self.loader_file_name = MavenArtifact(installer_json["path"]).file_name
        # [1.17.1, )
        elif self.installer_spec == 1:
            self.server_jar_path = (
                installer_json["serverJarPath"]
                .replace("{LIBRARY_DIR}", "libraries")
                .replace("{MINECRAFT_VERSION}", self.game_version)
                .replace("/", str(Path().anchor or Path("/")).strip("\\/") or "/")
                .lstrip("./")
            )
            self.server_jar_path = Path(*Path(self.server_jar_path).parts)
        else:
            raise RuntimeError(
                f"不支持 forge-{self.game_version}-{self.loader_version} 服务端预安装"
            )

        libs = []
        for doc in (installer_json, version_json):
            for lib in doc.get("libraries", []):
                artifact = lib.get("downloads", {}).get("artifact", {})
                maven_lib = _get_maven_lib(
                    lib["name"],
                    artifact.get("path"),
                    _replace_legacy_maven_url(artifact.get("url")),
                )
                if maven_lib:
                    libs.append(maven_lib)
        self.libraries = _distinct_by_artifact(libs)

        server_mappings = manifest.get("downloads", {}).get("server_mappings")
        if self.installer_spec == 1 and server_mappings:
            self.mappings = (
                FileEntry(RepoType.SERVER_MAPPINGS, self.game_version)
                .set_downloadable("server_mappings.txt", [server_mappings.get("url")])
                .with_size(server_mappings.get("size"))
                .with_sha1(server_mappings.get("sha1"))
            )
            return [*self.libraries, self.mappings]
        return self.libraries

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

        # 尝试生成允许 mojmap 缓存的安装包
        modified_installer = self._generate_modified_installer()

        # 执行安装
        ret = java.execute_jar(
            modified_installer or self.installer.local_path,
            ["--installServer", ".", "--offline"],
            self.temp_storage.work_space,
        )
        if ret != 0:
            raise RuntimeError(
                f"forge-{self.game_version}-{self.loader_version} 服务端预安装失败"
            )
        if modified_installer:
            Path(modified_installer).unlink(missing_ok=True)

        title = (
            self.server_name
            or f"Forge Server {self.game_version} {self.loader_version}"
        )
        files = []
        launcher_script_name = None

        # 自行创建脚本
        if self.installer_spec in (-1, 0):
            assert self.loader_file_name is not None
            if (Path(self.temp_storage.work_space) / self.loader_file_name).exists():
                launcher_script_name = generate_script(
                    self.temp_storage.work_space,
                    java.dist_name,
                    self.loader_file_name,
                    title,
                    self.ram,
                ).archive_entry_name
                files.extend(java.get_jre_files())
        # 修改forge自带脚本
        else:
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

    def _generate_modified_installer(self):
        if self.mappings is None:
            return None
        assert self.installer is not None
        with zipfile.ZipFile(self.installer.local_path) as src_zip:
            try:
                profile_json = json.loads(
                    src_zip.read("install_profile.json").decode("utf-8")
                )
            except KeyError:
                return None
            mojmap_artifact_name = None
            for processor_json in profile_json.get("processors", []):
                args_json = processor_json.get("args") or []
                if "DOWNLOAD_MOJMAPS" in args_json:
                    args_json.append("--skipIfExists")
                    value = (
                        profile_json.get("data", {}).get("MOJMAPS", {}).get("server")
                    )
                    if isinstance(value, str):
                        mojmap_artifact_name = value.strip("[]")
                    break
            if not mojmap_artifact_name:
                return None

            dst_installer_path = Path(self.temp_storage.work_space) / "installer.jar"
            with zipfile.ZipFile(
                dst_installer_path, "w", zipfile.ZIP_DEFLATED
            ) as dst_zip:
                dst_zip.writestr(
                    "install_profile.json",
                    json.dumps(profile_json, ensure_ascii=False, separators=(",", ":")),
                )
                for entry in src_zip.infolist():
                    if entry.filename == "install_profile.json" or (
                        entry.filename.startswith("META-INF")
                        and entry.filename.endswith((".SF", ".RSA"))
                    ):
                        continue
                    dst_zip.writestr(entry, src_zip.read(entry))

            dst_mapping_file = (
                Path(self.temp_storage.work_space)
                / "libraries"
                / MavenArtifact(mojmap_artifact_name).file_path
            )
            dst_mapping_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.mappings.local_path, dst_mapping_file)
            return dst_installer_path

    def close(self):
        self.temp_storage.dispose()


def _replace_legacy_maven_url(url):
    return (
        url.replace("//files.minecraftforge.net/maven/", "//maven.minecraftforge.net/")
        if url
        else None
    )


def _get_maven_lib(artifact_id, path, provided_url):
    if not provided_url:
        return None
    maven_file = (
        MavenFileEntry(artifact_id)
        .with_maven_url(provided_url)
        .with_maven_base_archive_entry_name()
    )
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
