import re
import zipfile
from pathlib import Path

from api.fabric_api_client import FabricApiClient
from server_installer.abstract_mod_server_installer import \
    AbstractModServerInstaller
from server_installer.maven_file_entry import MavenFileEntry
from storage.file_entry import FileEntry
from storage.local_storage import LocalStorage
from storage.repo_type import RepoType
from utils.jar_launcher_utils import generate_script
from utils.jar_utils import read_jar_manifest, write_jar_manifest


class FabricServerInstaller(AbstractModServerInstaller):
    legacy_installer_version = "0.11.2"
    legacy_loader_version = "0.12.5"
    default_launcher_manifest_main_class = (
        "net.fabricmc.loader.launch.server.FabricServerLauncher"
    )
    services_dir = "META-INF/services/"

    def __init__(self):
        super().__init__()
        self.api = FabricApiClient()
        self.manifest = None
        self.libraries = []
        self.temp_storage = LocalStorage.get_temp_storage("fabric-install")

    def resolve_standalone_loader_jar(self):
        meta = self.api.get_installer_meta()
        installer_version = next(
            (item.get("version") for item in meta if item.get("stable")),
            self.legacy_installer_version,
        )
        file = self._resolve_standalone_server_jar(installer_version)
        if file is None and installer_version != self.legacy_installer_version:
            file = self._resolve_standalone_server_jar(self.legacy_installer_version)
        return [file] if file else []

    def is_preinstallation_supported(self) -> bool:
        return True

    def _resolve_standalone_server_jar(self, installer_version):
        file_name = f"fabric-server-{self.game_version}-{self.loader_version}-{installer_version}.jar"
        file = FileEntry(RepoType.MOD_LOADER_JAR, file_name).with_archive_entry_name(
            file_name
        )
        if file.validate():
            return file
        url = self.api.get_server_loader_url(
            self.game_version, self.loader_version, installer_version
        )
        if not url:
            return None
        return file.set_downloadable(file_name, [url])

    def resolve_installer(self):
        return []

    def resolve_installer_dependencies(self, manifest):
        self.manifest = self.api.get_server_manifest(
            self.game_version, self.loader_version
        )
        self.libraries = [
            MavenFileEntry(lib["name"])
            .with_maven_repo(lib["url"])
            .with_maven_base_archive_entry_name()
            for lib in self.manifest.get("libraries", [])
        ]
        return self.libraries

    def preinstall(self, java, server_jar):
        embeded_lib = _version_tuple(self.loader_version) <= _version_tuple(
            self.legacy_loader_version
        )
        launcher_file = self._generate_launcher(embeded_lib)
        jre_files = java.get_jre_files()
        script_file = generate_script(
            self.temp_storage.work_space,
            java.dist_name,
            launcher_file.archive_entry_name,
            self.server_name
            or f"Fabric Server {self.game_version} {self.loader_version}",
            self.ram,
        )
        server_jar.with_archive_entry_name("server.jar")
        eula_file = self.generate_eula_agreement_file(self.temp_storage.work_space)

        files = [launcher_file, server_jar, script_file, eula_file]
        if not embeded_lib:
            files.extend(self.libraries)
        files.extend(jre_files)
        return files

    # https://github.com/FabricMC/fabric-installer/blob/e73f4466e157f586472ec6c6cec5f8d1cc9dddaa/src/main/java/net/fabricmc/installer/server/ServerInstaller.java
    def _generate_launcher(self, embeded_lib):
        assert self.manifest is not None
        file_name = f"fabric-server-{self.game_version}-{self.loader_version}.jar"
        file = FileEntry(
            self.temp_storage, RepoType.MOD_LOADER_JAR, file_name
        ).with_archive_entry_name(file_name)
        Path(file.local_path).parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(
            file.local_path, "w", zipfile.ZIP_DEFLATED
        ) as launcher_jar:
            manifest = {
                "Manifest-Version": "1.0",
                "Main-Class": self._get_launcher_main_class(),
            }
            if not embeded_lib:
                manifest["Class-Path"] = " ".join(
                    lib.archive_entry_name
                    for lib in self.libraries
                    if lib.archive_entry_name
                )
            write_jar_manifest(launcher_jar, manifest)

            # linux下也是CRLF
            launcher_jar.writestr(
                "fabric-server-launch.properties",
                f"launch.mainClass={self.manifest.get('mainClass')}\r\n",
            )

            if embeded_lib:
                self._embed_libraries(launcher_jar)
        return file

    def _embed_libraries(self, launcher_jar):
        service_files = {}
        existing = set(launcher_jar.namelist())
        for lib in self.libraries:
            with zipfile.ZipFile(lib.local_path) as lib_jar:
                for entry in lib_jar.infolist():
                    if not entry.filename or entry.is_dir():
                        continue
                    # 服务列表
                    if (
                        entry.filename.startswith(self.services_dir)
                        and "/" not in entry.filename[len(self.services_dir) :]
                    ):
                        services = service_files.setdefault(entry.filename, set())
                        for raw_line in (
                            lib_jar.read(entry)
                            .decode("utf-8", errors="replace")
                            .splitlines()
                        ):
                            line = raw_line.split("#", 1)[0].strip()
                            if line:
                                services.add(line)
                    # 签名文件
                    elif re.match(
                        r"META-INF/[^/]+\.(SF|DSA|RSA|EC)", entry.filename, re.I
                    ):
                        continue
                    # 重复文件
                    elif entry.filename in existing:
                        continue
                    else:
                        launcher_jar.writestr(
                            entry.filename, lib_jar.read(entry), zipfile.ZIP_DEFLATED
                        )
                        existing.add(entry.filename)
        # write service definitions
        for entry_name, services in service_files.items():
            if services:
                launcher_jar.writestr(entry_name, "\n".join(sorted(services)) + "\n")

    def _get_launcher_main_class(self):
        loader = next(
            (
                lib
                for lib in self.libraries
                if re.match(r"net\.fabricmc:fabric-loader:.*", lib.artifact.id, re.I)
            ),
            None,
        )
        if loader is None:
            return self.default_launcher_manifest_main_class
        with zipfile.ZipFile(loader.local_path) as jar:
            manifest = read_jar_manifest(jar)
        return manifest.get("Main-Class") or self.default_launcher_manifest_main_class

    def close(self):
        self.temp_storage.dispose()
        self.api.close()


def _version_tuple(value):
    numbers = re.findall(r"\d+", str(value))
    return tuple(int(number) for number in numbers[:3])
