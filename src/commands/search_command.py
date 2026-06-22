from rich.table import Table

from commands.options.http_options import parse_http_args
from global_style import console
from services.ftb_service import FTBService
from services.http_config_service import HttpConfigService


def run(args):
    options, positionals = parse_http_args(args)
    HttpConfigService.setup_http(options)
    if not positionals:
        raise RuntimeError("缺少搜索关键词")
    with FTBService() as ftb:
        items = ftb.search(" ".join(positionals))
    table = Table()
    table.add_column("ID")
    table.add_column("名称")
    for modpack_id, name in items:
        table.add_row(str(modpack_id), name)
    console.print(table)
    return 0
