import locale
import tempfile
from pathlib import Path

from feedtheforge.i18n import Locale

# 自动切换语言
default_locale = locale.getdefaultlocale()[0]
lang = Locale("zh_CN" if default_locale == "zh_CN" else "en_US")
current_language = lang.get_language()

# 缓存目录设置
cache_dir = Path(tempfile.gettempdir()) / "FeedTheForge"
packlist_path = cache_dir / "packlist.json"
modpack_path = cache_dir / "pack_files"
patch = cache_dir / "patch.zip"
patch_folder = cache_dir / "patch"
mod_path = modpack_path / "overrides" / "mods"

I18NUPDATE_LINK = "https://mediafilez.forgecdn.net/files/5335/196/I18nUpdateMod-3.5.5-all.jar"

# API链接
API_LIST = "https://api.modpacks.ch/public/modpack/all"
API_FEATURED = "https://api.modpacks.ch/public/modpack/featured/20"
API_SEARCH = "https://api.modpacks.ch/public/modpack/search/20/detailed?platform=modpacksch&term="

# 全部汉化 key: FTB唯一包版本 vaule: 蓝奏云汉化下载链接
# TODO　未来应单独做出一个json并联网更新，不宜写死。支持匹配id全部版本支持
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
    "11937": "https://wulian233.lanzouj.com/ib5G81wnrpwb",
    "12266": "https://wulian233.lanzouj.com/ib5G81wnrpwb"
}
