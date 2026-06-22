import os
from contextlib import suppress


def is_running_by_double_click():
    if os.name != "nt":
        return False
    with suppress(Exception):
        import ctypes

        process_ids = (ctypes.c_ulong * 2)()
        count = ctypes.windll.kernel32.GetConsoleProcessList(process_ids, 2)
        return count == 1
    return False


def set_console_title(title):
    if os.name != "nt":
        return
    with suppress(Exception):
        import ctypes

        ctypes.windll.kernel32.SetConsoleTitleW(str(title))
