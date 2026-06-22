from mirrors.imirror import HostReplacementMirror


class CreeperHostMirror(HostReplacementMirror):
    cn = False
    replace_table = {"maven.minecraftforge.net": ["maven.creeperhost.net"]}
