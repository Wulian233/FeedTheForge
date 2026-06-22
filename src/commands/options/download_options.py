from commands.options.http_options import HttpOptions, next_value


class DownloadOptions(HttpOptions):
    def __init__(self):
        super().__init__()
        self.server = False
        self.preinstall = False
        self.thread = None
        self.output = "."
        self.curseforge_key = None

    def read_option(self, arg, iterator):
        if super().read_option(arg, iterator):
            return True
        if arg in ("-s", "--server"):
            self.server = True
            return True
        if arg == "--agree-minecraft-eula":
            self.preinstall = True
            return True
        if arg in ("--preinstall", "--pre-install"):
            self.preinstall = True
            return True
        if arg in ("-t", "--thread"):
            self.thread = int(next_value(iterator, arg))
            return True
        if arg in ("-o", "--output"):
            self.output = next_value(iterator, arg)
            return True
        if arg in ("-k", "--curse-key"):
            self.curseforge_key = next_value(iterator, arg)
            return True
        return False
