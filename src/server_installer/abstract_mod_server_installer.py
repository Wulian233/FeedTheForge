from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

from storage.file_entry import FileEntry


class AbstractModServerInstaller(ABC):
    def __init__(self):
        self.game_version = ""
        self.loader_version = ""
        self.server_name = ""
        self.ram = 0

    def resolve_standalone_loader_jar(self):
        return []

    def is_preinstallation_supported(self) -> bool:
        return False

    # 不需要时才返回空，获取失败直接throw
    @abstractmethod
    def resolve_installer(self):
        raise NotImplementedError

    @abstractmethod
    def resolve_installer_dependencies(self, manifest):
        raise NotImplementedError

    @abstractmethod
    def preinstall(self, java, server_jar):
        raise NotImplementedError

    @staticmethod
    def generate_eula_agreement_file(directory):
        file = FileEntry(str(Path(directory) / "eula.txt")).with_archive_entry_name(
            "eula.txt"
        )
        Path(file.local_path).write_text(
            f"# Minecraft EULA https://aka.ms/MinecraftEULA.\n# {datetime.now(UTC)} UTC\neula=true\n",
            encoding="utf-8",
        )
        return file

    def close(self):
        return None
