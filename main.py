import asyncio
import json
import os
import shutil
from pick import pick, Option

from feedtheforge import utils
from feedtheforge.async_downloader import AsyncDownloader
from feedtheforge.const import *


async def download_files(files):
    tasks = []
    async with AsyncDownloader() as dl:
        for file_info in files:
            file_path = file_info["path"][2:]
            file_name = file_info["name"]
            full_path = os.path.join(modpack_path, "overrides", file_path)
            output_path = os.path.join(full_path, file_name)

            if not os.path.exists(output_path):
                await utils.create_directory(full_path)
                # 将任务添加到列表中
                tasks.append(dl.download_file(file_info["url"], output_path))

        await asyncio.gather(*tasks)


async def load_modpack_data(modpack_id: str) -> dict:
    """异步加载整合包数据"""
    modpack_id_path = os.path.join(cache_dir, f"pack-{modpack_id}.json")
    url = f"https://api.modpacks.ch/public/modpack/{modpack_id}"
    
    async with AsyncDownloader() as dl:
        data = await dl.fetch_json(url)

    with open(modpack_id_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    return data

async def display_modpack_list(load_json):
    """读取json并制作对应的选择菜单"""
    options = []
    with open(load_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        for modpack in data["packs"]:
            # 处理字典形式的数据，即搜索整合包
            if isinstance(modpack, dict): modpack_id = modpack['id']
            # 直接是ID的情况，即查看流行的整合包
            else: modpack_id = modpack
            # 屏蔽模组加载器
            if modpack_id in [116, 104, 81, 105]:
                continue
            modpack_data = await load_modpack_data(modpack_id)
            modpack_name = modpack_data['name']
            
            options.append(Option(f"{modpack_name} (id: {modpack_id})", modpack_id))
    # 防止搜索结果为空
    if not options:
        print(lang.t("feedtheforge.main.empty_search"))
        utils.pause()

    title = lang.t("feedtheforge.start.title")
    selected_modpack = pick(options, title, indicator="=>")
    return selected_modpack[0].value


async def download_featured_modpack():
    featured_json = os.path.join(cache_dir, "featured_modpacks.json")
    # 检查7天内有没有缓存，加快速度
    if not await utils.is_recent_file(featured_json):
        async with AsyncDownloader() as dl:
            await dl.download_file(API_FEATURED, featured_json)

    # 下载选择的整合包
    modpack_id = await display_modpack_list(featured_json)
    await download_modpack(modpack_id)


async def search_modpack():
    import string

    search_json = os.path.join(cache_dir, "search_modpacks.json")
    keyword = input(lang.t("feedtheforge.main.search_modpack"))
    # 防止搜索为空或不是英文字母数字
    if not keyword or not all(char in string.printable for char in keyword):
        print(lang.t("feedtheforge.main.empty_search"))
        utils.pause()

    async with AsyncDownloader() as dl:
        await dl.download_file(API_SEARCH + keyword, search_json)
    # 下载选择的整合包
    modpack_id = await display_modpack_list(search_json)
    await download_modpack(modpack_id)

async def apply_chinese_patch(lanzou_url: str) -> None:
    """蓝奏云直链解析下载汉化并自动覆盖应用汉化"""
    from feedtheforge.lanzou import LanzouDownloader
    from zipfile import ZipFile
    # 获取返回的json中downUrl的值为下载链接
    data = json.loads(LanzouDownloader().get_direct_link(lanzou_url))
    down_url = data.get("downUrl")    
    async with AsyncDownloader() as dl:
        await dl.download_file(down_url, patch)
        
    with ZipFile(patch, 'r') as zip_ref:
        zip_ref.extractall(patch_folder)
    os.remove(patch)
    # 把汉化移动剪切到整合包临时目录完成汉化
    for root, _, files in os.walk(patch_folder):
        for file in files:
            patch_file = os.path.join(root, file)
            relative_path = os.path.relpath(patch_file, patch_folder)
            target_path = os.path.join(modpack_path, "overrides", relative_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.move(patch_file, target_path)
    shutil.rmtree(patch_folder)


async def download_modpack(modpack_id: str) -> None:
    print(lang.t("feedtheforge.main.modpack_name", modpack_name=modpack_name))

    modpack_data = await load_modpack_data(modpack_id)
    modpack_name = modpack_data["name"]
    modpack_author = modpack_data["authors"][0]["name"]
    versions = modpack_data["versions"]
    version_list = [version["id"] for version in versions]
    
    print(lang.t("feedtheforge.main.version_list", version_list=version_list))
    selected_version = input(lang.t("feedtheforge.main.enter_version"))
    # 输入为空且有版本可下载（更保险），取最新版本
    if not selected_version and version_list:
        selected_version = str(max(int(version) for version in version_list))
        print(lang.t("feedtheforge.main.default_version", selected_version=selected_version))
    # id无对应整合包或不是数字
    else:
        print(lang.t("feedtheforge.main.invalid_modpack_version"))
        utils.pause()


    async with AsyncDownloader() as dl:
        download_url = f"https://api.modpacks.ch/public/modpack/{modpack_id}/{selected_version}"
        await dl.download_file(download_url, os.path.join(cache_dir, "download.json"))
        await prepare_modpack_files(modpack_name, modpack_author, selected_version)

    if current_language == "zh_CN":
        async with AsyncDownloader() as dl:
            # 切片[-27:]恰为模组文件名
            await dl.download_file(I18NUPDATE_LINK, os.path.join(mod_path, I18NUPDATE_LINK[-27:]))
        # 检查有无对应汉化
        if str(selected_version) in all_patch:
            install = input(lang.t("feedtheforge.main.has_chinese_patch"))
            if install.lower() == "y":
                await apply_chinese_patch(all_patch[selected_version])

    utils.zip_modpack(modpack_name)


async def prepare_modpack_files(modpack_name, modpack_author, modpack_version):
    os.makedirs(modpack_path, exist_ok=True)
    with open(os.path.join(cache_dir, "download.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
     # 下面均为CurseForge整合包识别的固定格式
    mc_version = data["targets"][1]["version"]
    modloader_name = data["targets"][0]["name"]
    modloader_version = data["targets"][0]["version"]

    curse_files, non_curse_files = [], []
    for file_info in data["files"]:
        if "curseforge" in file_info:
            curse_files.append({
                "fileID": file_info["curseforge"]["file"],
                "projectID": file_info["curseforge"]["project"],
                "required": True
            })
        else:
            non_curse_files.append(file_info)

    modloader_id = f"{modloader_name}-{modloader_version}"
    if modloader_name == "neoforge" and mc_version == "1.20.1":
        modloader_id = f"{modloader_name}-{mc_version}-{modloader_version}"

    manifest_data = {
        "author": modpack_author,
        "files": curse_files,
        "manifestType": "minecraftModpack",
        "manifestVersion": 1,
        "minecraft": {
            "version": mc_version,
            "modLoaders": [{"id": modloader_id, "primary": True}]
        },
        "name": modpack_name,
        "overrides": "overrides",
        "version": modpack_version
    }

    with open(os.path.join(modpack_path, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=4)
    
    # FIXME 生成 modlist.html 文件
    modlist_file = os.path.join(modpack_path, "modlist.html")
    with open(modlist_file, "w", encoding="utf-8") as f:
        f.write("<ul>\n")
        # for file_info in curse_files:
        #     mod_page_url = file_info.get("url", "#")
        #     f.write(f'<li><a href="{mod_page_url}">{file_info["fileID"]}</a></li>\n')
        f.write("</ul>\n")

    os.makedirs(os.path.join(modpack_path, "overrides"), exist_ok=True)
    await download_files(non_curse_files)


async def fetch_modpack_list():
    print(lang.t("feedtheforge.main.getting_list"))
    try:
        async with AsyncDownloader() as dl:
            modpacks_data = await dl.fetch_json(API_LIST)
            with open(packlist_path, "w", encoding="utf-8") as f:
                json.dump(modpacks_data, f, indent=4)
    except OSError:
        print(lang.t("feedtheforge.main.getting_error"))
        utils.pause()

    # 从本地文件读取数据
    with open(packlist_path, "r", encoding="utf-8") as f:
        modpacks_data = json.load(f)
    
    global all_pack_ids
    all_pack_ids = [str(pack_id) for pack_id in modpacks_data.get("packs", [])]
    print(all_pack_ids)

async def main():
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 本地化中这里的字中间要有空格，不加空格VSCode终端正常，在cmd中字会重叠
    title = lang.t("feedtheforge.start.title")
    options = [
        Option(lang.t("feedtheforge.start.featured_modpack"), 
               description=lang.t("feedtheforge.start.featured_modpack_desc")),
        Option(lang.t("feedtheforge.start.search_modpack"), 
               description=lang.t("feedtheforge.start.search_modpack_desc")),
        Option(lang.t("feedtheforge.start.enter_id"), 
               description=lang.t("feedtheforge.start.enter_id_desc")),
        Option(lang.t("feedtheforge.start.clean_temp"), 
               description=lang.t("feedtheforge.start.clean_temp_desc")),
        Option(lang.t("feedtheforge.start.exit"), 
               description=lang.t("feedtheforge.start.exit_desc"))
    ]

    option, index = pick(options, title, indicator="=>")

    # 根据选择执行相应的操作
    if index == 0: 
        await download_featured_modpack()
    elif index == 1:
        await search_modpack()
    elif index == 2:
        await fetch_modpack_list()
        modpack_id = input(lang.t("feedtheforge.main.enter_id"))
        if modpack_id not in all_pack_ids:
            print(lang.t("feedtheforge.main.invalid_pack_id"))
            return
        await download_modpack(modpack_id)
    elif index == 3:
        utils.clean_temp()
        utils.pause()
