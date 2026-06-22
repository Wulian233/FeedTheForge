class FTBModpack:
    def __init__(
        self,
        modpack_id,
        name,
        authors,
        summary,
        readme,
        home_page_url,
        icon,
        version,
        runtime,
        files,
    ):
        self.id = modpack_id
        self.name = name
        self.authors = authors
        self.summary = summary
        self.readme = readme
        self.home_page_url = home_page_url
        self.icon = icon
        self.version = version
        self.runtime = runtime
        self.files = files


class VersionInfo:
    def __init__(self, version_id, name, version_type):
        self.id = version_id
        self.name = name
        self.type = version_type


class RuntimeInfo:
    def __init__(
        self,
        game_version,
        mod_loader_type,
        mod_loader_version,
        java_version,
        minimum_ram,
        recommended_ram,
    ):
        self.game_version = game_version
        self.mod_loader_type = mod_loader_type
        self.mod_loader_version = mod_loader_version
        self.java_version = java_version
        self.minimum_ram = minimum_ram
        self.recommended_ram = recommended_ram
