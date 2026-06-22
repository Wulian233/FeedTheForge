import os
import random
import sys
from pathlib import Path

import httpx
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.containers import AnyContainer
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Label, RadioList

from global_style import console, error, focused, success
from services.ftb_service import FTBService
from services.http_config_service import HttpConfigService


class BackRequested(Exception):
    pass


PAGE_SIZE = 10
PROMPT_STYLE = Style.from_dict(
    {
        "prompt-title": "cyan",
        "prompt-hint": "cyan",
        "prompt-list": "",
        "prompt-item": "white",
        "prompt-selected": "ansiyellow bold",
        "prompt-number": "white",
    }
)


def run(_args):
    setup_output_directory(Path.cwd(), True)
    check_terminal()
    HttpConfigService.setup_http_proxy(False, None)

    with FTBService() as ftb:
        while True:
            try:
                op = prompt(
                    "按上下键选择，回车确认，Esc退出:",
                    "查看热门整合包",
                    "搜索整合包",
                    "输入整合包ID",
                    "列出所有整合包",
                    "管理缓存",
                )
                if op == 0:
                    result = select_featured_modpack(ftb)
                elif op == 1:
                    result = search_modpack(ftb)
                elif op == 2:
                    result = input_id(ftb)
                elif op == 3:
                    result = list_modpack(ftb)
                elif op == 4:
                    manage_cache()
                    result = None
                else:
                    result = None
                if result is not None:
                    return result
            except BackRequested:
                return 0


def select_featured_modpack(ftb):
    packs = load("加载热门整合包...", ftb.get_featured_modpacks)
    return select_modpack(ftb, packs)


def manage_cache():
    from commands.cache_command import run_tui

    return run_tui()


def list_modpack(ftb):
    packs = load("加载整合包列表...", ftb.list)
    return select_modpack(ftb, packs)


def search_modpack(ftb):
    keyword = console.input(focused("\n输入关键词:")).strip()
    result = load("搜索整合包...", ftb.search, keyword.strip())
    if not result:
        error("搜索结果为空")
        return None
    return select_modpack(ftb, result)


def select_modpack(ftb, packs):
    if len(packs) > 1:
        packs = sorted(packs, key=lambda item: item[0], reverse=True)
        while True:
            try:
                index = prompt(
                    "选择整合包，Esc返回:",
                    *[f"{name} （{pack_id}）" for pack_id, name in packs],
                )
                result = select_versions(ftb, packs[index][0])
                if result is not None:
                    return result
            except BackRequested:
                return None
    return select_versions(ftb, packs[0][0])


def input_id(ftb):
    while True:
        value = console.input(focused("\n输入整合包ID:")).strip()
        while not value.isdigit():
            error("请输入数字ID")
            value = console.input(focused("\n输入整合包ID:")).strip()
        try:
            return select_versions(ftb, int(value))
        except httpx.HTTPStatusError as ex:
            if ex.response.status_code == 404:
                error(f"整合包 ID 不存在：{value}")
                continue
            raise


def select_versions(ftb, pack_id):
    info = load("加载整合包版本...", ftb.get_modpack_info, pack_id)
    success(f"整合包：{info.get('name')}（{info.get('id')}）")

    versions = sorted(
        info.get("versions", []), key=lambda item: item.get("id", 0), reverse=True
    )
    while True:
        try:
            index = prompt(
                "选择整合包版本，Esc返回:",
                *[format_version(version) for version in versions],
            )
            version = versions[index]
            success(f"版本：{version.get('name')}（{version.get('id')}）")
            return download(ftb, info, version)
        except BackRequested:
            return None


def download(ftb, info, version):
    while True:
        server = (
            prompt("选择整合包类型，Esc返回:", "客户端 - 用来玩", "服务端 - 用来开服")
            == 1
        )
        try:
            light = (
                server
                or prompt(
                    "选择下载类型，Esc返回:",
                    "标准包 - 体积较大，由本工具下载大多数文件并打包（推荐）",
                    "轻量包 - 体积极小，由启动器在导入时下载所有文件",
                )
                == 1
            )
            preinstall = (
                server
                and prompt(
                    "是否预安装服务端，并且同意 MC 用户协议：https://aka.ms/MinecraftEULA，Esc返回",
                    "是，并且同意该协议",
                    "否，稍后手动安装",
                )
                == 0
            )
            break
        except BackRequested:
            continue
    output = Path.cwd()

    if server:
        success("类型：服务端" + ("（预安装）" if preinstall else ""))
    else:
        success("类型：客户端" + ("（轻量包）" if light else "（标准包）"))

    success(f"保存位置: {output}")
    console.print()
    wait_any_key("按任意键开始下载...")
    console.print()

    pack = ftb.get_modpack(info, version["id"])
    ftb.download_modpack(pack, server, preinstall if server else not light, output)
    return 0


def prompt(title, *selections):
    if not selections:
        raise BackRequested

    index = 0
    window_size = min(PAGE_SIZE, len(selections))
    height = window_size
    bindings = KeyBindings()
    options = [(i, selection) for i, selection in enumerate(selections)]
    radio_list = RadioList(
        options,
        default=index,
        select_on_focus=True,
        open_character="",
        select_character=">",
        close_character="",
        container_style="class:prompt-list",
        default_style="",
        selected_style="class:prompt-selected",
        checked_style="class:prompt-selected",
        number_style="class:prompt-number",
        show_cursor=False,
        show_scrollbar=len(selections) > window_size,
    )

    @bindings.add("enter", eager=True)
    def _enter(event):
        event.app.exit(result=radio_list.current_value)

    @bindings.add("escape")
    def _escape(event):
        event.app.exit(exception=BackRequested())

    @bindings.add("c-c")
    def _ctrl_c(event):
        event.app.exit(exception=KeyboardInterrupt())

    @bindings.add("up", eager=True)
    @bindings.add("k", eager=True)
    def _up(event):
        radio_list._selected_index = (radio_list._selected_index - 1) % len(options)
        radio_list._handle_enter()

    @bindings.add("down", eager=True)
    @bindings.add("j", eager=True)
    def _down(event):
        radio_list._selected_index = (radio_list._selected_index + 1) % len(options)
        radio_list._handle_enter()

    items_window = Window(
        content=radio_list.control,
        style="class:prompt-list",
        right_margins=radio_list.window.right_margins,
        height=Dimension.exact(height),
        wrap_lines=False,
        dont_extend_height=True,
    )
    children: list[AnyContainer] = [Label([("class:prompt-title", "\n" + title)])]
    if len(selections) > window_size:
        children.append(
            Label(
                [
                    (
                        "class:prompt-hint",
                        f"共 {len(selections)} 项，按 ↑↓ 键翻页，Esc返回",
                    )
                ]
            )
        )
    children.append(items_window)
    app = Application(
        layout=Layout(HSplit(children), focused_element=items_window),
        key_bindings=bindings,
        style=PROMPT_STYLE,
        full_screen=False,
        erase_when_done=True,
    )
    return app.run()


def format_version(version):
    version_type = str(version.get("type", "")).lower()
    name = version.get("name")
    version_id = version.get("id")
    if version_type == "release":
        return f"{name} 正式版 （{version_id}）"
    if version_type == "beta":
        return f"{name} 测试版 （{version_id}）"
    if version_type in ("alpha", "archived"):
        return f"{name} 内测&BUG版 （{version_id}）"
    return f"{name} {version_type} （{version_id}）"


def wait_any_key(message):
    console.print(focused(message))
    if os.name == "nt":
        import msvcrt

        msvcrt.getch()
    else:
        input()


def load(message, func, *args):
    with console.status(f"[yellow bold]{message}[/yellow bold]"):
        return func(*args)


def setup_output_directory(path, is_default_command):
    path = Path(path).resolve()
    directory = (
        path.parent if path.is_file() or str(path).lower().endswith(".zip") else path
    )
    test_file = directory / str(abs(random.randrange(1 << 63)))
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w+b"):
            pass
        test_file.unlink(missing_ok=True)
    except Exception as ex:
        if is_default_command:
            raise RuntimeError(
                "当前目录无写入权限，请把程序移动到其他目录再试。"
            ) from ex
        raise RuntimeError(f"输出目录 {directory} 无写入权限，请指定其它目录。") from ex


def check_terminal():
    if sys.stdin.isatty() and sys.stdout.isatty():
        return
    if os.name == "nt":
        raise RuntimeError(
            "当前终端不支持无参启动，请使用 Windows Terminal 打开本程序，"
            "或指定具体的命令行参数，或升级操作系统至 win10 1607 或更高版本"
        )
    raise RuntimeError("当前终端不支持无参启动，请指定具体的命令行参数，或换用其它终端")
