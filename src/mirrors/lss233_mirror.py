from mirrors.imirror import HostReplacementMirror


class Lss233Mirror(HostReplacementMirror):
    replace_table = {
        (
            "maven.minecraftforge.net",
            "libraries.minecraft.net",
        ): [
            "crystal.app.lss233.com/repositories/minecraft",
            "maven.fastmirror.net/repositories/minecraft",
        ]
    }
