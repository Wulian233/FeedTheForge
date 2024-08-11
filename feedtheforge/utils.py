import os
import shutil

from feedtheforge.const import *
from pick import pick, Option


async def create_directory(path):
    """
    创建目录，如果目录不存在则创建
    """
    os.makedirs(path, exist_ok=True)

async def is_recent_file(filepath, days=7):
    """
    检查文件最后修改时间是否在指定天数内

    :param filepath: 文件路径
    :param days: 距离当前的天数间隔，默认值为7天
    :return: 如果文件存在且最后修改时间在指定天数内，返回 True 否则返回 False
    """
    from datetime import datetime, timedelta

    if not os.path.exists(filepath):
        return False
    modification_date = datetime.fromtimestamp(os.path.getmtime(filepath)).date()
    current_date = datetime.now().date()
    if current_date - modification_date < timedelta(days=days):
        return True
    return False

def zip_modpack(modpack_name):
    """
    压缩整合包文件夹为一个zip文件
    
    :param modpack_name: 整合包的名称
    """
    from zipfile import ZIP_DEFLATED, ZipFile

    print(lang.t("feedtheforge.utils.zipping_modpack"))

    with ZipFile(f"{modpack_name}.zip", "w", ZIP_DEFLATED) as zf:
        for dirname, _, files in os.walk(modpack_path):
            for filename in files:
                file_path = os.path.join(dirname, filename)
                zf.write(file_path, os.path.relpath(file_path, modpack_path))

    print(lang.t("feedtheforge.utils.modpack_created", modpack_name=f"{modpack_name}.zip"))
    shutil.rmtree(modpack_path, ignore_errors=True)

def clean_temp():
    """
    清理缓存目录中的临时文件
    """
    size = 0
    for root, _, files in os.walk(cache_dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    shutil.rmtree(cache_dir, ignore_errors=True)
    print(lang.t("feedtheforge.utils.clean_temp", size=int(size / 1024)))

def pause():
    """
    退出程序
    """
    if os.name == 'nt': 
        os.system('pause')
    else:
        input(lang.t("feedtheforge.utils.pause"))
    exit(0)

def client_server():
    title = lang.t("feedtheforge.utils.type_title")
    options = [
        Option(lang.t("feedtheforge.utils.client"), 
               description=lang.t("feedtheforge.utils.client_desc")),
        Option(lang.t("feedtheforge.utils.server"), 
               description=lang.t("feedtheforge.utils.server_desc")),
    ]

    option, index = pick(options, title, indicator="=>")

    return index

def server_os():
    title = lang.t("feedtheforge.utils.os_title")
    options = [
        Option("Linux"),
        Option("Windows"),
        Option("Mac"),
        Option("Linux (arm)"),
        Option("Mac (arm)"),
    ]

    option, index = pick(options, title, indicator="=>")

    return index