from mirrors.imirror import HostReplacementMirror


class BmclMirror(HostReplacementMirror):
    replace_table = {
        (
            "launcher.mojang.com",
            "launchermeta.mojang.com",
            "piston-meta.mojang.com",
            "piston-data.mojang.com",
            "files.minecraftforge.net",
        ): "bmclapi2.bangbang93.com",
        (
            "libraries.minecraft.net",
            "maven.minecraftforge.net",
            "maven.fabricmc.net",
            "maven.neoforged.net",
        ): "bmclapi2.bangbang93.com/maven",
    }
