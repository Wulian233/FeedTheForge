from rich.table import Table

from global_style import console, success, warn
from storage.local_storage import LocalStorage, persistent_storage


def run(args):
    if not args or args[0] in ("list", "show", "view"):
        if len(args) > 1:
            raise RuntimeError("cache list 不接受额外参数")
        return _show_cache()
    if args[0] in ("clear", "clean"):
        if len(args) > 2:
            raise RuntimeError("cache clear 最多接受一个缓存名称")
        return _clear_cache(args[1] if len(args) == 2 else None)
    raise RuntimeError(f"未知 cache 子命令: {args[0]}")


def run_tui():
    from commands.default_command import BackRequested, prompt, wait_any_key

    storage = persistent_storage()
    while True:
        entries = list(storage.iter_cache_entries())
        if not entries:
            warn("没有持久缓存")
            wait_any_key("按任意键返回...")
            return 0

        selections = [
            f"{entry.name}    {entry.files} 个文件    {entry.size_text}"
            for entry in entries
        ]
        selections.append("清理可用临时缓存")
        try:
            index = prompt("选择要查看的缓存，Esc返回:", *selections)
        except BackRequested:
            return 0

        if index == len(entries):
            LocalStorage.prune_unused_temp()
            success("已清理可用临时缓存")
            wait_any_key("按任意键继续...")
            continue

        entry = entries[index]
        _print_entry(entry)
        try:
            action = prompt(
                "选择操作，Esc返回:",
                f"删除 {entry.name}",
                "返回缓存列表",
            )
        except BackRequested:
            continue
        if action == 1:
            continue

        try:
            confirm = prompt(
                f"确认删除 {entry.name}？",
                "取消",
                "确认删除",
            )
        except BackRequested:
            continue
        if confirm == 1:
            cleared = storage.clear_cache(entry.name)
            if cleared:
                success("已清除缓存: " + ", ".join(cleared))
            else:
                warn("没有找到可清除的缓存")
            wait_any_key("按任意键继续...")


def _show_cache():
    storage = persistent_storage()
    table = Table()
    table.add_column("名称")
    table.add_column("文件数", justify="right")
    table.add_column("大小", justify="right")
    table.add_column("路径")

    entries = list(storage.iter_cache_entries())
    for entry in entries:
        table.add_row(entry.name, str(entry.files), entry.size_text, str(entry.path))

    console.print(f"持久缓存目录: {storage.root_dir}")
    if entries:
        console.print(table)
    else:
        warn("没有持久缓存")

    temp_entries = list(LocalStorage.iter_temp_cache_entries())
    if temp_entries:
        temp_table = Table()
        temp_table.add_column("临时缓存")
        temp_table.add_column("文件数", justify="right")
        temp_table.add_column("大小", justify="right")
        temp_table.add_column("路径")
        for entry in temp_entries:
            temp_table.add_row(
                entry.name, str(entry.files), entry.size_text, str(entry.path)
            )
        console.print(temp_table)
    return 0


def _print_entry(entry):
    table = Table()
    table.add_column("名称")
    table.add_column("文件数", justify="right")
    table.add_column("大小", justify="right")
    table.add_column("路径")
    table.add_row(entry.name, str(entry.files), entry.size_text, str(entry.path))
    console.print(table)


def _clear_cache(name):
    storage = persistent_storage()
    cleared = storage.clear_cache(name)
    LocalStorage.prune_unused_temp()
    if cleared:
        success("已清除缓存: " + ", ".join(cleared))
    else:
        warn("没有找到可清除的缓存")
    return 0
