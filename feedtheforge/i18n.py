import json
from pathlib import Path
from string import Template


class Locale:
    def __init__(self, lang: str):
        self.lang = lang
        self.path = Path(f"./feedtheforge/lang/{lang}.json")
        self.data = {}
        self.load()

    def __getitem__(self, key: str):
        return self.data[key]

    def __contains__(self, key: str):
        return key in self.data

    def load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            d = f.read()
            self.data = json.loads(d)
            f.close()

    def get_string(self, key: str, failed_prompt):
        n = self.data.get(key, None)
        if n != None:
            return n
        if failed_prompt:
            return str(key) + self.t("feedtheforge.i18n.failed")
        return key

    def t(self, key: str, failed_prompt=True, *args, **kwargs):
        localized = self.get_string(key, failed_prompt)
        return Template(localized).safe_substitute(*args, **kwargs)

    def get_language(self):
        return self.lang
    
lang = Locale("zh_CN")