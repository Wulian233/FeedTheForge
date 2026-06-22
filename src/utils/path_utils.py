import re
from pathlib import Path


def escape_file_name(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(".") or "modpack"


def setup_output_directory(output, clean):
    path = Path(output)
    directory = path.parent if path.suffix.lower() == ".zip" else path
    if clean and directory.exists():
        for child in directory.iterdir():
            if child.is_file():
                child.unlink()
    directory.mkdir(parents=True, exist_ok=True)
    return path
