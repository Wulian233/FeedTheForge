import locale
import os
import tempfile

from feedtheforge.i18n import Locale

# 自动切换语言
if locale._getdefaultlocale()[0] == "zh_CN":
    lang = Locale("zh_CN")
else:
    lang = Locale("en_US")
    
current_language = lang.get_language()

cache_dir = os.path.join(tempfile.gettempdir(), "FeedTheForge")
packlist_path = os.path.join(cache_dir, "packlist.json")
modpack_path = os.path.join(cache_dir, "pack_files")

patch = os.path.join(cache_dir, "patch.zip")
patch_folder = os.path.join(cache_dir, "patch")
i18nupdate_link = "https://mediafilez.forgecdn.net/files/5335/196/I18nUpdateMod-3.5.5-all.jar"
mod_path = os.path.join(modpack_path, "overrides", "mods")

api_list = "https://api.modpacks.ch/public/modpack/all"
api_featured = "https://api.modpacks.ch/public/modpack/featured/20"
api_search = "https://api.modpacks.ch/public/modpack/search/20/detailed?platform=modpacksch&term="

# 全部汉化 key: FTB唯一包版本 vaule: 蓝奏云汉化下载链接
all_patch = {
    # 100 StoneBlock 3
    "6498": "https://wulian233.lanzouj.com/iwAZ61xg3yib",
    "6647": "https://wulian233.lanzouj.com/iwAZ61xg3yib",
    "6967": "https://wulian233.lanzouj.com/iwAZ61xg3yib",
    "11655": "https://wulian233.lanzouj.com/iwAZ61xg3yib",
    # 115 Arcanum Institute
    "11512": "https://vmhanhuazu.lanzouj.com/i8W7Y1nr83le",
    # 122 Builders Paradise 2
    "11840": "https://wulian233.lanzouj.com/ib5G81wnrpwb",
    "11937": "https://wulian233.lanzouj.com/ib5G81wnrpwb"
}
