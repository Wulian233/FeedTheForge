from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from api.ftb.ftb_api_client import FTBApiClient
from packs.modrinth_modpack_processor import ModrinthModpackProcessor
from packs.server_modpack_processor import ServerModpackProcessor
from services.http_config_service import HttpConfigService
from services.model.ftb_file_entry import FTBFileEntry
from services.model.ftb_modpack import FTBModpack, RuntimeInfo, VersionInfo
from storage.file_entry import FileEntry
from storage.local_storage import persistent_storage
from storage.repo_type import RepoType


class FTBService:
    # Minecraft, Minecraft Forge, NeoForge, Fabric
    black_list = {81, 104, 116, 105}

    def __init__(self):
        self.ftb = FTBApiClient()
        self._info_cache = {}

    @staticmethod
    def data(rsp):
        return rsp.get("data", rsp) if isinstance(rsp, dict) else rsp

    def get_featured_modpacks(self):
        ids = self.data(self.ftb.get_featured()).get("packs", [])
        return self._pack_names(ids)

    def list(self):
        ids = self.data(self.ftb.get_list()).get("packs", [])
        return self._pack_names(
            [modpack_id for modpack_id in ids if modpack_id not in self.black_list]
        )

    def search(self, keyword):
        data = self.data(self.ftb.search(keyword))
        packs = data.get("packs") or data.get("results") or []
        result = []
        for item in packs:
            if isinstance(item, int):
                info = self.get_modpack_info(item)
                result.append((info.get("id", item), info.get("name", str(item))))
            else:
                result.append(
                    (
                        item.get("id"),
                        item.get("name") or item.get("title") or str(item.get("id")),
                    )
                )
        return result

    def get_modpack_info(self, modpack_id):
        if modpack_id in self._info_cache:
            return self._info_cache[modpack_id]

        info = self.data(self.ftb.get_info(modpack_id))
        self._info_cache[modpack_id] = info
        return info

    def get_modpack(self, modpack_or_id, version_id):
        info = (
            modpack_or_id
            if isinstance(modpack_or_id, dict)
            else self.get_modpack_info(modpack_or_id)
        )
        manifest = self._get_manifest(info["id"], version_id)
        version = self._find_version(info, version_id)
        runtime = self._runtime(info, manifest, version_id)
        files = [FTBFileEntry(file) for file in manifest.get("files", [])]
        icon = self._icon(info)
        return FTBModpack(
            info["id"],
            info.get("name") or f"Modpack {info['id']}",
            [
                a.get("name", str(a)) if isinstance(a, dict) else str(a)
                for a in info.get("authors", [])
            ],
            info.get("synopsis") or info.get("summary") or "",
            info.get("description") or info.get("readme") or "",
            info.get("url")
            or info.get("website")
            or f"https://www.feed-the-beast.com/modpacks/{info['id']}",
            icon,
            version,
            runtime,
            files,
        )

    @staticmethod
    def download_modpack(pack, server, preinstall, output):
        processor = (
            ServerModpackProcessor(pack, preinstall)
            if server
            else ModrinthModpackProcessor(pack, preinstall)
        )
        processor.download()
        processor.process()
        output = Path(output)
        if output.exists() and output.is_dir() or output.suffix.lower() != ".zip":
            output.mkdir(parents=True, exist_ok=True)
            target = output / processor.default_file_name
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            target = output
        with open(target, "wb") as fp:
            processor.pack(fp, str(target))
        return target

    def _pack_names(self, ids):
        ids = list(ids)
        if not ids:
            return []

        def update(cache):
            cache = cache or {"items": {}}
            items = cache.setdefault("items", {})
            missing_ids = [
                modpack_id for modpack_id in ids if str(modpack_id) not in items
            ]
            max_workers = max(1, min(HttpConfigService.thread, len(missing_ids)))
            if missing_ids:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for info in executor.map(self.get_modpack_info, missing_ids):
                        items[str(info["id"])] = {
                            "name": info.get("name", str(info["id"]))
                        }
            return cache

        cache = persistent_storage().get_or_update_object(
            "list", update, "ModpackCache"
        )
        items = cache.get("items") or {}
        return [
            (
                modpack_id,
                (items.get(str(modpack_id)) or {}).get("name", str(modpack_id)),
            )
            for modpack_id in ids
        ]

    def _get_manifest(self, modpack_id, version_id):
        storage = persistent_storage()

        def update(cached):
            if not isinstance(cached, dict):
                return self.data(self.ftb.get_manifest(modpack_id, version_id))
            files = cached.get("files") or []
            if files and all(
                (file.get("hashes") or {}).get("sha512") for file in files
            ):
                return cached
            return self.data(self.ftb.get_manifest(modpack_id, version_id))

        return storage.get_or_update_object(
            f"manifest-{modpack_id}-{version_id}", update, "FtbModpackManifest"
        )

    @staticmethod
    def _find_version(info, version_id):
        versions = info.get("versions") or []
        selected = next(
            (item for item in versions if item.get("id") == version_id), None
        )
        if selected is None:
            raise RuntimeError("Version id 不正确")
        return VersionInfo(
            version_id,
            selected.get("name") or str(version_id),
            selected.get("type") or selected.get("version_type") or "",
        )

    @staticmethod
    def _runtime(info, manifest, version_id):
        targets = manifest.get("targets") or []
        target_by_type = {
            str(item.get("type", "")).lower(): item
            for item in targets
            if isinstance(item, dict)
        }
        specs = manifest.get("specs") or {}
        minecraft = target_by_type.get("game") or {}
        loader = target_by_type.get("modloader") or {}
        java = target_by_type.get("runtime") or {}
        return RuntimeInfo(
            minecraft.get("version") or "",
            loader.get("name") or "",
            loader.get("version") or "",
            str(java.get("version") or "8.0.312"),
            int(specs.get("minimum") or 0),
            int(specs.get("recommended") or 0),
        )

    @staticmethod
    def _icon(info):
        art = info.get("art") or []
        if isinstance(art, dict):
            art = list(art.values())
        for item in art:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "square":
                continue
            item = {str(key): value for key, value in item.items()}
            url = ""
            for key, value in item.items():
                if key in ("url", "link") and value:
                    url = str(value)
                    break
            if not url:
                continue
            return (
                FileEntry(RepoType.ICON, str(info["id"]))
                .with_size(item.get("size") or None)
                .set_unrequired()
                .set_downloadable("icon.png", [url])
                .with_archive_entry_name("icon.png")
            )
        return None

    def close(self):
        self.ftb.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
