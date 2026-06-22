from commands.options.download_options import DownloadOptions
from global_style import success
from services.ftb_service import FTBService
from services.http_config_service import HttpConfigService
from utils.path_utils import setup_output_directory


def run(args):
    options = parse(args)
    setup_output_directory(options["output"], False)
    HttpConfigService.setup_http(
        thread=options["thread"],
        proxy=options["proxy"],
        user_agent=options["user_agent"],
        curse_key=options["curse_key"],
        no_proxy=options["no_proxy"],
    )
    with FTBService() as ftb:
        if options["version_id"] == 0:
            info = ftb.get_modpack_info(options["pack_id"])
            options["version_id"] = max(
                (item.get("id", 0) for item in info.get("versions", [])), default=0
            )
            success(f"√ Latest version id {options['version_id']} selected")
            pack = ftb.get_modpack(info, options["version_id"])
        else:
            pack = ftb.get_modpack(options["pack_id"], options["version_id"])

        if options["server"] and options["preinstall"]:
            pack_type = "Server Preinstalled"
        elif options["server"]:
            pack_type = "Server"
        elif options["light"]:
            pack_type = "Client Light"
        else:
            pack_type = "Client"
        success(f"√ {pack.name} v{pack.version.name}({pack.version.type}) {pack_type}")
        target = ftb.download_modpack(
            pack,
            options["server"],
            options["preinstall"] if options["server"] else not options["light"],
            options["output"],
        )
        success(f"√ 输出: {target}")
    return 0


def parse(args):
    download_options = DownloadOptions()
    light = True
    positionals = []
    iterator = iter(args)
    for arg in iterator:
        if download_options.read_option(arg, iterator):
            continue
        if arg in ("-l", "--light"):
            light = True
        elif arg in ("-f", "--full"):
            light = False
        elif arg.startswith("-"):
            raise RuntimeError(f"未知选项: {arg}")
        else:
            positionals.append(arg)
    if not positionals:
        raise RuntimeError("缺少整合包ID")
    if len(positionals) > 2:
        raise RuntimeError("参数过多")
    proxy = None if download_options.no_proxy else download_options.proxy
    options = {
        "pack_id": int(positionals[0]),
        "version_id": 0,
        "output": download_options.output,
        "server": download_options.server,
        "preinstall": download_options.preinstall,
        "light": light,
        "thread": download_options.thread,
        "proxy": proxy,
        "no_proxy": download_options.no_proxy,
        "user_agent": download_options.user_agent,
        "curse_key": download_options.curseforge_key,
    }
    if len(positionals) > 1:
        options["version_id"] = int(positionals[1])
    return options
