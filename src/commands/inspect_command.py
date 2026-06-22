from rich.table import Table

from commands.options.http_options import parse_http_args
from global_style import console
from services.ftb_service import FTBService
from services.http_config_service import HttpConfigService


def run(args):
    options, positionals = parse_http_args(args)
    HttpConfigService.setup_http(options)
    if not positionals:
        raise RuntimeError("缺少整合包ID")
    if len(positionals) > 1:
        raise RuntimeError("参数过多")
    modpack_id = int(positionals[0])
    with FTBService() as ftb:
        info = ftb.get_modpack_info(modpack_id)
    table = Table(show_header=False)
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("ID", str(info.get("id", modpack_id)))
    table.add_row("名称", info.get("name", ""))
    table.add_row("简介", info.get("synopsis") or info.get("summary") or "")
    table.add_row("版本数", str(len(info.get("versions") or [])))
    table.add_row(
        "作者",
        ", ".join(
            a.get("name", str(a)) if isinstance(a, dict) else str(a)
            for a in info.get("authors", [])
        ),
    )
    console.print(table)
    return 0
