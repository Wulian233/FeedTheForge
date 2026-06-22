import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "src" / "program.py"

NAME = "FeedTheForge"
DIST_PATH = ROOT / "dist"
WORK_PATH = ROOT / "build/pyinstaller/work"
SPEC_PATH = ROOT / "build/pyinstaller/spec"
ICON_PATH = ROOT / "scripts" / "icon.ico"
UPX_DIR = Path(os.environ["UPX_DIR"]) if "UPX_DIR" in os.environ else None
CLEAN = True

EXCLUDED_MODULES = [
    "_tkinter",
    "idlelib",
    "tcl",
    "tk",
    "tkinter",
]


def main(extra_args=None) -> int:
    ensure_pyinstaller()

    if CLEAN:
        for path in (DIST_PATH, WORK_PATH, SPEC_PATH):
            shutil.rmtree(path, ignore_errors=True)
            path.mkdir(parents=True, exist_ok=True)

        for pycache in ROOT.rglob("__pycache__"):
            shutil.rmtree(pycache, ignore_errors=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--optimize",
        "2",
        "--name",
        NAME,
        "--icon",
        str(ICON_PATH),
        "--paths",
        str(ROOT / "src"),
        "--distpath",
        str(DIST_PATH),
        "--workpath",
        str(WORK_PATH),
        "--specpath",
        str(SPEC_PATH),
        str(ENTRYPOINT),
    ]

    for module in EXCLUDED_MODULES:
        command.extend(["--exclude-module", module])

    if platform.system() != "Windows":
        command.append("--strip")

    if UPX_DIR:
        command.extend(["--upx-dir", str(UPX_DIR)])

    if extra_args:
        command[3:3] = extra_args

    print("Building FeedTheForge with PyInstaller")
    print("Command:", " ".join(command))

    return subprocess.run(command, cwd=ROOT).returncode


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        raise SystemExit("PyInstaller 未安装，请先安装")


if __name__ == "__main__":
    extra = sys.argv[1:]
    raise SystemExit(main(extra))
