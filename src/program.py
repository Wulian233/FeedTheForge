import argparse
import sys

from app_info import AUTHOR, NAME, VERSION
from commands import (cache_command, default_command, download_command,
                      featured_command, inspect_command, list_command,
                      search_command)
from download.download_queue import DownloadCancelled
from global_style import error
from storage.local_storage import LocalStorage, persistent_storage
from utils.error_utils import handle_exception
from utils.native_utils import is_running_by_double_click, set_console_title

commands = {
    "cache": cache_command.run,
    "download": download_command.run,
    "inspect": inspect_command.run,
    "featured": featured_command.run,
    "search": search_command.run,
    "list": list_command.run,
}

USAGE_EPILOG = """\
详细用法:
    feed-the-forge
    feed-the-forge featured [HTTP选项]
    feed-the-forge list [HTTP选项]
    feed-the-forge search <关键词> [HTTP选项]
    feed-the-forge inspect <整合包ID> [HTTP选项]
    feed-the-forge download <整合包ID> [版本ID] [下载选项]
    feed-the-forge cache [list]
    feed-the-forge cache clear [缓存名称]

HTTP选项:
    -n, --no-proxy          不使用 HTTP 代理
    -p, --proxy <代理>      显式指定 HTTP 代理
    -u, --user-agent <UA>   指定 User-Agent

下载选项:
    -s, --server                     下载服务端
    --agree-minecraft-eula           预安装服务端，并同意 MC 用户协议
    -t, --thread <数量>               并行下载数
    -o, --output <路径>               输出目录或文件路径
    -k, --curse-key <Key>             CurseForge API Key
    -l, --light                       下载轻量客户端
    -f, --full                        下载标准客户端
"""


def app():
    set_console_title(f"{NAME} v{VERSION} - {AUTHOR}")
    LocalStorage.prune_unused_temp()
    persistent_storage().clean_legacy_asset_cache()
    args = sys.argv[1:]
    ret = 1
    try:
        if args and args[0] in ("-h", "--help", "help"):
            print(_parser().format_help())
            ret = 0
            return ret
        if args and args[0] in ("-v", "--version", "version"):
            print(VERSION)
            ret = 0
            return ret
        if not args:
            ret = default_command.run(args)
            return ret
        parsed, command_args = _parse_args(args)
        runner = commands[parsed.command]
        ret = runner(command_args)
        return ret
    except DownloadCancelled as ex:
        error(str(ex))
        ret = 1
        return ret
    except KeyboardInterrupt:
        error("已取消")
        ret = 1
        return ret
    except Exception as ex:
        handle_exception(ex)
        ret = 1
        return ret
    finally:
        LocalStorage.prune_unused_temp()
        if is_running_by_double_click():
            print()
            if ret == 0:
                print("按任意键退出...", end="", flush=True)
            else:
                print("发生了错误，按任意键退出...", end="", flush=True)
            try:
                import msvcrt

                msvcrt.getch()
            except Exception:
                input()


def _parser():
    parser = argparse.ArgumentParser(
        prog="feed-the-forge",
        description="下载和打包 Feed The Beast 整合包",
        epilog=USAGE_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        exit_on_error=False,
        suggest_on_error=True,
        color=True,
    )
    parser.add_argument("-v", "--version", action="store_true", help="查看版本信息")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.add_parser("cache", help="查看或清除缓存")
    subparsers.add_parser("download", help="下载整合包")
    subparsers.add_parser("inspect", help="查看整合包详情")
    subparsers.add_parser("featured", help="列出热门整合包")
    subparsers.add_parser("search", help="搜索整合包")
    subparsers.add_parser("list", help="列出所有整合包")
    return parser


def _parse_args(args):
    try:
        parsed, command_args = _parser().parse_known_args(args)
    except argparse.ArgumentError as ex:
        raise RuntimeError(str(ex)) from None
    if parsed.version:
        print(VERSION)
        raise SystemExit(0)
    if parsed.command is None:
        raise RuntimeError("缺少命令")
    return parsed, command_args


if __name__ == "__main__":
    raise SystemExit(app())
