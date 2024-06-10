import aiohttp
import asyncio
from urllib import request
from feedtheforge.const import *
import json
import os
import shutil
from zipfile import ZIP_DEFLATED, ZipFile
from pick import pick, Option

async def download_file(session, url, output_path):
    async with session.get(url) as response:
        with open(output_path, "wb") as f:
            while chunk := await response.content.read(1024):
                f.write(chunk)

async def _create_directory(path):
    os.makedirs(path, exist_ok=True)

async def download_mod_files(session, non_curse_files):
    tasks = []
    for file_info in non_curse_files:
        mod_file_path = file_info["path"][2:]
        mod_file_name = file_info["name"]
        full_path = os.path.join(modpack_path, "overrides", mod_file_path)
        output_path = os.path.join(full_path, mod_file_name)
        
        if not os.path.exists(output_path):
            await _create_directory(full_path)
            tasks.append(download_file(session, file_info["url"], output_path))
    
    await asyncio.gather(*tasks)

async def _featured_and_search(load_json):
    # 读取json并制作对应的选择菜单
    options = []
    with open(load_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        for modpack_id in data["packs"]:
            get_modpack_info(modpack_id)
            with open(modpack_id_path, "r", encoding="utf-8") as pack_file:
                pack_data = json.load(pack_file)
                print(f"{pack_data['name']} (id {modpack_id}）")
                options.append(Option(f"{pack_data['name']}（ id：{modpack_id}）", modpack_id))
    title = lang.t("feedtheforge.start.title")
    modpack_id = pick(options, title, indicator="=>")
    modpack_id = modpack_id[0].value
    # 下载选择的整合包
    await download_modpack(modpack_id)

async def get_featured_modpack():
    featured_json = os.path.join(cache_dir, "featured_modpacks.json")
    async with aiohttp.ClientSession() as session:
        await download_file(session, api_featured, featured_json)
    
    await _featured_and_search(featured_json)

async def search_modpack():
    # print("未完成，敬请期待")
    search_json = os.path.join(cache_dir, "search_modpacks.json")
    keyword = input(lang.t("feedtheforge.main.search_modpack"))
    async with aiohttp.ClientSession() as session:
        await download_file(session, api_search + keyword, search_json)
    
    # await _featured_and_search(search_json)
    os.remove(search_json)

def get_modpack_info(modpack_id):
    global modpack_id_path
    modpack_id_path = os.path.join(cache_dir, f"pack-{modpack_id}.json")
    with request.urlopen(f"https://api.modpacks.ch/public/modpack/{modpack_id}") as response:
        data = json.loads(response.read().decode("utf-8"))

    with open(modpack_id_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=4))

async def chinese_patch(lanzou_url):
    # 蓝奏云api直链解析下载
    async with aiohttp.ClientSession() as session:
        await download_file(session, f"https://tool.bitefu.net/lz?url={lanzou_url}", patch)
    with ZipFile(patch, 'r') as zip_ref:
        zip_ref.extractall(patch_folder)
    os.remove(patch)
    # 把汉化补丁移动剪切到整合包
    for root, _, files in os.walk(patch_folder):
        for file in files:
            patch_file = os.path.join(root, file)
            shutil.move(patch_file, modpack_path)
    shutil.rmtree(patch_folder)

async def download_modpack(modpack_id):
    get_modpack_info(modpack_id)
    with open(modpack_id_path, "r", encoding="utf-8") as f:
        modpack_data = json.load(f)

    modpack_name = modpack_data["name"]
    modpack_author = modpack_data["authors"][0]["name"]
    modpack_version = modpack_data["versions"][0]["name"]
    print(lang.t("feedtheforge.main.modpack_name", modpack_name = modpack_name))
    versions = modpack_data["versions"]
    version_list = [version["id"] for version in versions]
    print(lang.t("feedtheforge.main.version_list", version_list = version_list))
    selected_version = input(lang.t("feedtheforge.main.enter_version"))

    # 输入为空且有版本可下载（更保险），取最新版本
    if not selected_version and version_list:
        selected_version = max(version_list)
        print(lang.t("feedtheforge.main.default_version", selected_version = selected_version))
    # id无效，无对应整合包
    elif int(selected_version) not in version_list:
        input(lang.t("feedtheforge.main.invalid_modpack_version"))
        return
    # 输入的不是数字，大错特错
    else:
        input(lang.t("feedtheforge.main.invalid_modpack_version"))
        return
    
    async with aiohttp.ClientSession() as session:
        await download_file(session, f"https://api.modpacks.ch/public/modpack/{modpack_id}/{selected_version}", 
                            os.path.join(cache_dir, "download.json"))
        await get_modpack_files(modpack_name, modpack_author, modpack_version, session)
    
    if current_language == "zh_cn":
        # 切片[-27:]恰为模组文件名
        request.urlretrieve(i18nupdate_link, os.path.join(mod_path, i18nupdate_link[-27:]))
        # 检查有无对应汉化
        if str(selected_version) in all_patch:
            install = input(lang.t("feedtheforge.main.has_chinese_patch"))
            if install == "Y" or install == "y":
                chinese_patch(selected_version, all_patch[selected_version])
            else: pass

    zip_modpack(modpack_name)

async def get_modpack_files(modpack_name, modpack_author, modpack_version, session):
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
            "modLoaders": [{
                "id": modloader_id, 
                "primary": True}]
            },
        "name": modpack_name,
        "overrides": "overrides",
        "version": modpack_version
    }

    with open(os.path.join(modpack_path, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=4)
    
    # 生成 modlist.html 文件
    modlist_file = os.path.join(modpack_path, "modlist.html")
    with modlist_file.open("w", encoding="utf-8") as f:
        f.write("<ul>\n")
        for file_info in curse_files:
            mod_page_url = file_info.get("url", "#")
            f.write(f'<li><a href="{mod_page_url}">{file_info["fileID"]}</a></li>\n')
        f.write("</ul>\n")

    os.makedirs(os.path.join(modpack_path, "overrides"), exist_ok=True)
    await download_mod_files(session, non_curse_files)

def zip_modpack(modpack_name):
    print(lang.t("feedtheforge.main.zipping_modpack"))

    with ZipFile(f"{modpack_name}.zip", "w", ZIP_DEFLATED) as zf:
        for dirname, _, files in os.walk(modpack_path):
            for filename in files:
                file_path = os.path.join(dirname, filename)
                zf.write(file_path, os.path.relpath(file_path, modpack_path))
    print(lang.t("feedtheforge.main.modpack_created", modpack_name=f"{modpack_name}.zip"))
    shutil.rmtree(modpack_path, ignore_errors=True)

def cleat_temp():
    size = 0
    for root, _, files in os.walk(cache_dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    shutil.rmtree(cache_dir, ignore_errors=True)
    print(lang.t("feedtheforge.main.clean_temp", size=int(size/1024)))

async def get_modpack_list():
    print(lang.t("feedtheforge.main.getting_list"))
    try:
        with request.urlopen(api_list) as response:
            if response.status == 200:
                modpacks_data = json.loads(response.read().decode("utf-8"))
                with open(packlist_path, "w", encoding="utf-8") as f:
                    json.dump(modpacks_data, f, indent=4)
    # 网络错误无法连接为OSError
    except OSError:
        input(lang.t("feedtheforge.main.getting_error"))
        exit(1)

    with open(packlist_path, "r", encoding="utf-8") as f:
        modpacks_data = json.load(f)
    global all_pack_ids
    all_pack_ids = [str(all_pack_ids) for all_pack_ids in modpacks_data["packs"]]

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
               description=lang.t("feedtheforge.start.clean_temp_desc"))
    ]
    options, index = pick(options, title, indicator="=>")

    if index == 0: 
        await get_featured_modpack()
    elif index == 1:
        await search_modpack()
    elif index == 2:
        await get_modpack_list()
        modpack_id = input(lang.t("feedtheforge.main.enter_id"))
        if modpack_id not in all_pack_ids:
            print(lang.t("feedtheforge.main.invalid_pack_id"))
            return
        await download_modpack(modpack_id)
    elif index == 3:
        cleat_temp()
        