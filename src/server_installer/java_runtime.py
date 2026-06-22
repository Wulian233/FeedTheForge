import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

from storage.file_entry import FileEntry
from storage.local_storage import LocalStorage


class JavaRuntime:
    def __init__(self, storage):
        self.storage = storage
        dirs = [path for path in Path(storage.work_space).iterdir() if path.is_dir()]
        if not dirs:
            raise RuntimeError("未知的JavaHome目录结构")
        if len(dirs) == 1:
            self.dist_name = dirs[0].name
            self.java_home = dirs[0]
        else:
            self.dist_name = (
                f"zulu-jre-{os.environ.get('PROCESSOR_ARCHITECTURE', 'x64').lower()}"
            )
            self.java_home = Path(storage.work_space)
        self.java_path = self.java_home / "bin"
        self.java_exe = self.java_path / ("java.exe" if os.name == "nt" else "java")

    @classmethod
    def from_archive(cls, archive_path):
        storage = LocalStorage.get_temp_storage("java")
        try:
            archive_path = str(archive_path)
            if archive_path.lower().endswith(".zip"):
                with zipfile.ZipFile(archive_path) as archive:
                    archive.extractall(storage.work_space)
            elif archive_path.lower().endswith(".tar.gz"):
                with tarfile.open(archive_path, "r:gz") as archive:
                    archive.extractall(storage.work_space)
            else:
                raise RuntimeError("不支持的Java压缩包类型：" + Path(archive_path).name)
            return cls(storage)
        except Exception:
            storage.dispose()
            raise

    def execute_jar(self, jar_path, args, work_dir):
        env = os.environ.copy()
        env["JAVA_HOME"] = str(self.java_home)
        env["PATH"] = f"{self.java_path}{os.pathsep}{env.get('PATH', '')}"
        cmd = [str(self.java_exe), "-jar", str(jar_path), *(args or [])]
        process = subprocess.run(
            cmd,
            cwd=work_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return process.returncode

    def get_jre_files(self):
        # jdk8-
        jre_dir = self.java_home / "jre"
        if jre_dir.exists():
            return self._get_files(jre_dir)

        # jdk9+
        if (self.java_home / "jmods").exists():
            jre_dir = self._jlink()
            if jre_dir:
                return self._get_files(jre_dir)

        # jre or fallback
        return self._get_files(self.java_home)

    def _get_files(self, directory):
        files = []
        directory = Path(directory)
        for path in directory.rglob("*"):
            if path.is_file():
                files.append(
                    FileEntry(str(path)).with_archive_entry_name(
                        self.dist_name, path.relative_to(directory).as_posix()
                    )
                )
        return files

    def _jlink(self):
        jre_path = self.java_home / "jre-jlink"
        if jre_path.exists():
            return jre_path
        jmods_path = self.java_home / "jmods"
        modules = ",".join(path.stem for path in jmods_path.glob("*.jmod"))
        jlink = self.java_path / ("jlink.exe" if os.name == "nt" else "jlink")
        ret = subprocess.run(
            [
                str(jlink),
                "--output",
                str(jre_path),
                "--module-path",
                str(jmods_path),
                "--add-modules",
                modules,
                "--strip-debug",
                "--no-man-pages",
                "--no-header-files",
            ],
            cwd=self.java_home,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        if ret != 0:
            shutil.rmtree(jre_path, ignore_errors=True)
            return None
        return jre_path

    def close(self):
        self.storage.dispose()
