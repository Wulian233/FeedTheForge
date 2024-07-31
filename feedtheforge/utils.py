import os
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

from feedtheforge.const import *


async def create_directory(path):
    """
    创建目录，如果目录不存在则创建
    """
    os.makedirs(path, exist_ok=True)

def zip_modpack(modpack_name):
    """
    压缩整合包文件夹为一个zip文件
    
    :param modpack_name: 整合包的名称
    """
    print(lang.t("feedtheforge.main.zipping_modpack"))

    with ZipFile(f"{modpack_name}.zip", "w", ZIP_DEFLATED) as zf:
        for dirname, _, files in os.walk(modpack_path):
            for filename in files:
                file_path = os.path.join(dirname, filename)
                zf.write(file_path, os.path.relpath(file_path, modpack_path))

    print(lang.t("feedtheforge.main.modpack_created", modpack_name=f"{modpack_name}.zip"))
    shutil.rmtree(modpack_path, ignore_errors=True)

def clean_temp():
    """
    清理缓存目录中的临时文件
    """
    size = 0
    for root, _, files in os.walk(cache_dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    shutil.rmtree(cache_dir, ignore_errors=True)
    print(lang.t("feedtheforge.main.clean_temp", size=int(size / 1024)))

def pause():
    """
    退出程序
    """
    if os.name == 'nt': 
        os.system('pause')
    else:
        input(lang.t("feedtheforge.main.pause"))
