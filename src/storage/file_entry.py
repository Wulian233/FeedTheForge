import hashlib
import os
from contextlib import suppress
from pathlib import Path

from storage.local_storage import persistent_storage


class FileEntry:
    def __init__(self, *args):
        if not args:
            raise ValueError("FileEntry 至少需要一个路径或存储位置参数")
        if len(args) == 1:
            local_path = args[0]
        else:
            storage = persistent_storage()
            if args[0] is storage:
                local_path = storage.get_file_path(args[1], *args[2:])
            elif hasattr(args[0], "get_file_path"):
                local_path = args[0].get_file_path(args[1], *args[2:])
            else:
                local_path = storage.get_file_path(args[0], *args[1:])
        self.local_path = str(local_path)
        self.local_temp_path = self.local_path + ".tmp"
        self.display_name = None
        self.archive_entry_name = None
        self.urls = []
        self.required = True
        self.unix_executable = False
        self.unreachable = False
        self.sha1 = None
        self.size = None
        self._sha1_file_path = self.local_path + ".sha1"
        self._validated = False
        self._is_sha1_file_required = False

    def set_unix_executable(self):
        self.unix_executable = True
        return self

    def set_unreachable(self):
        self.unreachable = True
        return self

    def set_unrequired(self):
        self.required = False
        return self

    def with_sha1(self, sha1):
        self.sha1 = sha1.lower() if sha1 else None
        return self

    def set_sha1_file_required(self):
        self._is_sha1_file_required = True
        return self

    def with_size(self, size):
        self.size = int(size) if size is not None else None
        return self

    def with_archive_entry_name(self, *entry_name):
        parts = []
        for name in entry_name:
            if name:
                cleaned = str(name).replace(os.sep, "/").lstrip(".").strip("/")
                if cleaned:
                    parts.append(cleaned)
        self.archive_entry_name = "/".join(parts)
        return self

    def set_downloadable(self, display_name, urls):
        self.display_name = display_name
        self.urls = [url for url in urls if url]
        self.unreachable = False
        return self

    def validate_temp_and_apply(self):
        if self._validate_internal(self.local_temp_path, False, True):
            target = Path(self.local_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            Path(self.local_temp_path).move(target)
            return True
        return False

    def validate(self, delete_if_unsure=True):
        if self._validated:
            return True
        return self._validate_internal(self.local_path, True, delete_if_unsure)

    def delete(self):
        self._delete(self.local_path)
        self._delete(self._sha1_file_path)

    def delete_temp(self):
        self._delete(self.local_temp_path)
        self._delete(self._sha1_file_path)

    def _delete(self, path):
        with suppress(OSError):
            Path(path).unlink(missing_ok=True)

    def _validate_internal(self, file_path, strict, delete_if_unsure):
        file = Path(file_path)
        sha1_file = Path(self._sha1_file_path)
        if not file.exists():
            return False

        # 已提供文件大小且不匹配
        if self.size is not None and file.stat().st_size != self.size:
            self._delete(file_path)
            self._delete(self._sha1_file_path)
            return False

        # 获取哈希
        provided_sha1 = None
        if self.sha1:
            provided_sha1 = bytes.fromhex(self.sha1)
        elif sha1_file.exists():
            provided_sha1 = sha1_file.read_bytes()
        elif strict:
            if delete_if_unsure:
                self._delete(file_path)
                self._delete(self._sha1_file_path)
            return False

        computed_sha1 = self.calculate_sha1(file)

        # 有哈希且不匹配
        if provided_sha1 is not None and computed_sha1 != provided_sha1:
            self._delete(file_path)
            self._delete(self._sha1_file_path)
            return False

        if not sha1_file.exists() and (
            self._is_sha1_file_required or provided_sha1 is None
        ):
            sha1_file.write_bytes(computed_sha1)

        self._validated = True
        return True

    def calculate_sha1(self, file):
        h = hashlib.sha1()
        with open(file, "rb") as fp:
            for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                h.update(chunk)
        return h.digest()
