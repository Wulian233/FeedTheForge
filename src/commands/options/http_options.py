class HttpOptions:
    def __init__(self):
        self.no_proxy = False
        self.proxy = None
        self.user_agent = None

    def read_option(self, arg, iterator):
        if arg in ("-n", "--no-proxy"):
            self.no_proxy = True
            return True
        if arg in ("-p", "--proxy"):
            self.proxy = next_value(iterator, arg)
            return True
        if arg in ("-u", "--user-agent"):
            self.user_agent = next_value(iterator, arg)
            return True
        return False


def parse_http_args(args):
    options = HttpOptions()
    positionals = []
    iterator = iter(args)
    for arg in iterator:
        if options.read_option(arg, iterator):
            continue
        if arg.startswith("-"):
            raise RuntimeError(f"未知选项: {arg}")
        positionals.append(arg)
    return options, positionals


def next_value(iterator, option):
    try:
        return next(iterator)
    except StopIteration as ex:
        raise RuntimeError(f"选项 {option} 缺少参数") from ex
