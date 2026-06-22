import os
from pathlib import Path

from storage.file_entry import FileEntry

TZ = "Asia/Shanghai"
DEFAULT_RAM = 6144


def generate_script(script_dir, jre_dir_name, launcher_jar_name, title, ram):
    if os.name == "nt":
        return generate_windows_script(
            script_dir, jre_dir_name, launcher_jar_name, title, ram
        )
    return generate_unix_script(script_dir, jre_dir_name, launcher_jar_name, title, ram)


def generate_windows_script(script_dir, jre_dir_name, launcher_jar_name, title, ram):
    # 应该没人用windows文件链接吧
    script = f"""@echo off
CHCP 936 >nul
title {title}

:: 分配内存大小
set RAM={ram or DEFAULT_RAM}M

set "JAVA_HOME=%~dp0%{jre_dir_name}"
set "PATH=%JAVA_HOME%\\bin;%PATH%"
set TZ={TZ}

java.exe ^
  -Xms%RAM% -Xmx%RAM% ^
  -Duser.timezone=%TZ% ^
  -Dlog4j2.formatMsgNoLookups=true ^
  -jar "{launcher_jar_name}"

echo.
echo 按任意退出...
pause >nul
"""
    file = FileEntry(str(Path(script_dir) / "run.bat")).with_archive_entry_name(
        "run.bat"
    )
    Path(file.local_path).write_text(script, encoding="gbk")
    return file


def generate_unix_script(script_dir, jre_dir_name, launcher_jar_name, title, ram):
    script = f"""#!/usr/bin/env sh
echo "{title}"

# 分配内存大小
RAM={ram or DEFAULT_RAM}M

scriptPath=$(which $0)
if [ -L $scriptPath ]; then
    sourceDir=$(dirname $(readlink -f $scriptPath))
else
    sourceDir=$(dirname $scriptPath)
fi
JAVA_HOME="${{sourceDir}}/{jre_dir_name}"
chmod +x "${{JAVA_HOME}}/bin/java"
PATH="${{JAVA_HOME}}/bin:${{PATH}}"
TZ={TZ}

java \\
  -Xms${{RAM}} -Xmx${{RAM}} \\
  -Djava.awt.headless=true \\
  -Duser.timezone=${{TZ}} \\
  -Dlog4j2.formatMsgNoLookups=true \\
  -jar "{launcher_jar_name}" \\
  nogui
"""
    file = (
        FileEntry(str(Path(script_dir) / "run.sh"))
        .with_archive_entry_name("run.sh")
        .set_unix_executable()
    )
    Path(file.local_path).write_text(script.replace("\r\n", "\n"), encoding="utf-8")
    return file


def inject_forge_script(script_dir, jre_dir_name, title, ram):
    script_dir = Path(script_dir)
    win_path = next(script_dir.glob("*.bat"), None)
    unix_path = next(script_dir.glob("*.sh"), None)
    jvm_args_path = next(script_dir.glob("*jvm*.txt"), None) or next(
        script_dir.glob("*args*.txt"), None
    )
    if win_path is None or unix_path is None or jvm_args_path is None:
        return None

    if os.name == "nt":
        unix_path.unlink(missing_ok=True)
        inject_forge_windows_script(win_path, jvm_args_path, jre_dir_name, title, ram)
        return win_path.name
    win_path.unlink(missing_ok=True)
    inject_forge_unix_script(unix_path, jvm_args_path, jre_dir_name, title, ram)
    return unix_path.name


def inject_forge_windows_script(script_path, jvm_args_path, jre_dir_name, title, ram):
    original_content = (
        Path(script_path).read_text(errors="replace").replace("\npause", "").strip()
    )
    script = f"""@echo off
CHCP 936 >nul
title {title}

:: 如要修改分配内存大小或其它JVM参数，编辑文件"{Path(jvm_args_path).name}"

set "JAVA_HOME=%~dp0%{jre_dir_name}"
set "PATH=%JAVA_HOME%\\bin;%PATH%"

:: --------------- Official Script ---------------

{original_content}

:: -----------------------------------------------

echo.
echo 按任意退出...
pause>nul
"""
    Path(script_path).write_text(script, encoding="gbk")
    inject_jvm_args_file(jvm_args_path, ram, False)


def inject_forge_unix_script(script_path, jvm_args_path, jre_dir_name, title, ram):
    original_content = Path(script_path).read_text(errors="replace").strip()
    script = f"""#!/usr/bin/env sh
echo "{title}"

# 如要修改分配内存大小或其它JVM参数，编辑文件"{Path(jvm_args_path).name}"

scriptPath=$(which $0)
if [ -L $scriptPath ]; then
    sourceDir=$(dirname $(readlink -f $scriptPath))
else
    sourceDir=$(dirname $scriptPath)
fi
JAVA_HOME="${{sourceDir}}/{jre_dir_name}"
chmod +x "${{JAVA_HOME}}/bin/java"
PATH="${{JAVA_HOME}}/bin:${{PATH}}"
TZ={TZ}

# --------------- Official Script ---------------

{original_content} nogui

# -----------------------------------------------
"""
    Path(script_path).write_text(script.replace("\r\n", "\n"), encoding="utf-8")
    inject_jvm_args_file(jvm_args_path, ram, True)


def inject_jvm_args_file(jvm_args_path, ram, awt_headless):
    path = Path(jvm_args_path)
    lines = (
        path.read_text(encoding="utf-8", errors="replace").splitlines()
        if path.exists()
        else []
    )
    has_mem_args = any(line.strip().startswith(("-Xmx", "-Xms")) for line in lines)
    with open(path, "a", encoding="utf-8") as fp:
        fp.write("\n\n")
        if awt_headless:
            fp.write("-Djava.awt.headless=true\n")
        fp.write(f"-Duser.timezone={TZ}\n")
        fp.write("-Dlog4j2.formatMsgNoLookups=true\n")
        if not has_mem_args:
            fp.write("\n# 分配内存大小\n")
            fp.write(f"-Xmx{ram or DEFAULT_RAM}M\n")
