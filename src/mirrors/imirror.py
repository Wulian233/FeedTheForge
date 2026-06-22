import httpx


class HostReplacementMirror:
    cn = True
    replace_table = {}

    def __init__(self, replace_table=None):
        replace_table = replace_table or self.replace_table
        self.replace_table = {}
        for source, targets in replace_table.items():
            if isinstance(source, str):
                sources = [source]
            else:
                sources = source
            if isinstance(targets, str):
                targets = [targets]
            for host in sources:
                self.replace_table[host] = list(targets)

    def hit(self, url):
        return httpx.URL(str(url)).host in self.replace_table

    def get_mirrors(self, url):
        parsed = httpx.URL(str(url))
        host_list = self.replace_table.get(parsed.host)
        if not host_list:
            return []
        return [replace_host(parsed, host) for host in host_list]


def replace_host(parsed, new_host):
    target = httpx.URL(f"{parsed.scheme}://{new_host}")
    path = f"{target.path.rstrip('/')}{parsed.path}"
    return str(
        parsed.copy_with(
            host=target.host,
            port=target.port,
            path=path,
        )
    )
