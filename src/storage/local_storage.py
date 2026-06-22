import json
import os
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir

import brotli
from platformdirs import user_data_dir

from app_info import NAME
from utils.data_size_utils import humanize
from utils.locker import Locker


@dataclass(frozen=True)
class CacheEntry:
    name: str
    path: Path
    files: int
    size: int

    @property
    def size_text(self):
        return humanize(self.size)


# 不是前端那个（
class LocalStorage:
    _temp_counter = 0

    def __init__(self, directory, persistent=True):
        self.root_dir = Path(directory)
        self.object_dir = self.root_dir / "obj"
        self.work_space = self.root_dir / "work-space"
        self.is_persistent = persistent
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.object_dir.mkdir(parents=True, exist_ok=True)
        self.work_space.mkdir(parents=True, exist_ok=True)
        self._locker = None if persistent else Locker.acquire_or_wait(self.root_dir)

    def get_workspace_files(self, archive_entry_prefix=None):
        from storage.file_entry import FileEntry

        for file in self.work_space.rglob("*"):
            if file.is_file():
                rel = file.relative_to(self.work_space).as_posix()
                yield FileEntry(str(file)).with_archive_entry_name(
                    archive_entry_prefix, rel
                )

    def get_object_path(self, name, kind="object"):
        directory = self.object_dir / kind
        directory.mkdir(parents=True, exist_ok=True)
        return directory / name

    def get_object(self, name, kind="object"):
        path = self.get_object_path(name, kind)
        with Locker.acquire_or_wait(path):
            return self._read_object(path)

    def _read_object(self, path):
        if not path.exists():
            return None
        try:
            return json.loads(brotli.decompress(path.read_bytes()).decode("utf-8"))
        except brotli.error, OSError, UnicodeDecodeError, json.JSONDecodeError:
            path.unlink(missing_ok=True)
            return None

    def save_object(self, name, obj, kind="object"):
        path = self.get_object_path(name, kind)
        with Locker.acquire_or_wait(path):
            self._write_object(path, obj)

    @staticmethod
    def _write_object(path, obj):
        data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        path.write_bytes(brotli.compress(data, quality=1))

    def get_or_save_object(self, name, provider, kind="object"):
        path = self.get_object_path(name, kind)
        with Locker.acquire_or_wait(path):
            value = self._read_object(path)
            if value is None:
                value = provider()
                self._write_object(path, value)
            return value

    def get_or_update_object(self, name, provider, kind="object"):
        path = self.get_object_path(name, kind)
        with Locker.acquire_or_wait(path):
            value = self._read_object(path)
            value = provider(value)
            self._write_object(path, value)
            return value

    def get_file_path(self, repo, *path_segments):
        path = self.root_dir / str(repo)
        for segment in path_segments:
            if isinstance(segment, (list, tuple)):
                for part in segment:
                    path /= str(part)
            elif segment:
                path /= str(segment)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @classmethod
    def get_temp_storage(cls, name=None):
        cls._temp_counter += 1
        if name is None:
            suffix = f"{os.getpid()}-{cls._temp_counter}"
        else:
            suffix = f"{name}-{random.randrange(1 << 63)}"
        return cls(Path(gettempdir()) / f"{NAME}-{suffix}", False)

    @staticmethod
    def prune_unused_temp():
        temp = Path(gettempdir())
        for directory in temp.glob(f"{NAME}*"):
            if directory.is_dir():
                locker = Locker.try_acquire(directory)
                if locker is None:
                    continue
                with locker:
                    shutil.rmtree(directory, ignore_errors=True)

    def clean_legacy_asset_cache(self):
        directory = Path(self.get_file_path("Asset"))
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)

    def iter_cache_entries(self):
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.object_dir.mkdir(parents=True, exist_ok=True)
        self.work_space.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.root_dir.iterdir(), key=lambda item: item.name.lower()):
            if path.is_dir():
                yield self.cache_entry(path.name, path)

    def clear_cache(self, name=None):
        if name in (None, "", "all", "*"):
            targets = [entry.path for entry in self.iter_cache_entries()]
        else:
            normalized = str(name).strip()
            aliases = {"objects": "obj", "workspace": "work-space"}
            target_name = aliases.get(normalized.lower(), normalized)
            targets = [self.root_dir / target_name]

        cleared = []
        for target in targets:
            if self._remove_cache_target(target):
                cleared.append(target.name)

        self.object_dir.mkdir(parents=True, exist_ok=True)
        self.work_space.mkdir(parents=True, exist_ok=True)
        return cleared

    @classmethod
    def iter_temp_cache_entries(cls):
        temp = Path(gettempdir())
        for directory in sorted(
            temp.glob(f"{NAME}*"), key=lambda item: item.name.lower()
        ):
            if directory.is_dir():
                yield cls.cache_entry(directory.name, directory)

    def dispose(self):
        if not self.is_persistent:
            shutil.rmtree(self.root_dir, ignore_errors=True)
            if self._locker:
                self._locker.release()

    @staticmethod
    def cache_entry(name, path):
        files = 0
        size = 0
        for child in path.rglob("*"):
            if child.is_file():
                files += 1
                try:
                    size += child.stat().st_size
                except OSError:
                    pass
        return CacheEntry(name, path, files, size)

    def _remove_cache_target(self, target):
        root = self.root_dir.resolve()
        try:
            resolved = target.resolve()
        except OSError:
            resolved = target.absolute()
        if not resolved.is_relative_to(root) or resolved == root:
            raise RuntimeError(f"拒绝清理存储根目录之外的路径: {target}")
        if not target.exists():
            return False
        shutil.rmtree(target, ignore_errors=True)
        return not target.exists()


PERSISTENT_STORAGE = LocalStorage(user_data_dir(NAME, appauthor=False), True)


def persistent_storage():
    return PERSISTENT_STORAGE
