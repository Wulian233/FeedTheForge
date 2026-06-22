from zipfile import ZIP_DEFLATED

LINE_END = "\r\n"
ENTRY_NAME = "META-INF/MANIFEST.MF"
MAX_LINE_SIZE = 72


def read_jar_manifest(archive):
    result = {}
    try:
        with archive.open(ENTRY_NAME) as fp:
            lines = fp.read().decode("utf-8", errors="replace").splitlines()
    except KeyError:
        return result

    current_key = None
    current_value = []
    for line in lines:
        if not line.strip():
            continue
        if line.startswith(" ") and current_key:
            current_value.append(line[1:].rstrip("\r"))
            continue
        if current_key:
            result[current_key] = "".join(current_value)
        split_index = line.find(":")
        if split_index < 0:
            current_key = None
            current_value = []
            continue
        current_key = line[:split_index]
        current_value = [line[split_index + 2 :].rstrip("\r")]
    if current_key:
        result[current_key] = "".join(current_value)
    return result


def write_jar_manifest(archive, values):
    content = []
    for key, value in values.items():
        value = str(value)
        if len(key) + 2 + len(value) <= MAX_LINE_SIZE:
            content.append(f"{key}: {value}{LINE_END}")
            continue
        content.append(f"{key}: ")
        index = 0
        while index < len(value):
            if index == 0:
                size = MAX_LINE_SIZE - len(key) - 2
                content.append(value[:size] + LINE_END)
                index += size
            else:
                size = min(MAX_LINE_SIZE - 1, len(value) - index)
                content.append(" " + value[index : index + size] + LINE_END)
                index += size
    content.append(LINE_END)
    archive.writestr(ENTRY_NAME, "".join(content).encode("utf-8"), ZIP_DEFLATED)
