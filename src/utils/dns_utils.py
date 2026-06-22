import ipaddress
import random
import socket
import threading
from contextlib import contextmanager, nullcontext

import httpx

ORIGINAL_GETADDRINFO = socket.getaddrinfo


class DnsUtils:
    cache = {}
    cache_lock = threading.Lock()
    patch_lock = threading.Lock()
    patch_count = 0
    state = threading.local()
    endpoints = (
        "https://dns.alidns.com/resolve",
        "https://cloudflare-dns.com/dns-query",
    )

    @classmethod
    def resolving(cls, enabled=True):
        return cls.resolver_patch() if enabled else nullcontext()

    @classmethod
    def resolve(cls, host, family=socket.AF_UNSPEC):
        if not isinstance(host, str):
            return []
        if cls.is_ip(host) or host == "localhost":
            return [host] if cls.matches_family(host, family) else []
        cache_key = (host, family)
        with cls.cache_lock:
            cached = cls.cache.get(cache_key)
        if cached is not None:
            return cached

        addresses = cls.resolve_doh(host, family)
        if not addresses:
            try:
                infos = ORIGINAL_GETADDRINFO(host, None, family)
                addresses = [info[4][0] for info in infos]
            except OSError:
                addresses = []
        addresses = [
            address
            for address in dict.fromkeys(addresses)
            if cls.matches_family(address, family)
        ]
        with cls.cache_lock:
            cls.cache[cache_key] = addresses
        return addresses

    @classmethod
    def resolve_doh(cls, host, family):
        query_types = cls.query_types(family)
        if not query_types:
            return []

        results = []
        cls.state.resolving_doh = True
        try:
            with httpx.Client(http2=True, timeout=5, trust_env=False) as client:
                for query_type, answer_type in query_types:
                    headers = {"accept": "application/dns-json"}
                    for endpoint in cls.endpoints:
                        try:
                            response = client.get(
                                endpoint,
                                params={"name": host, "type": query_type},
                                headers=headers,
                            )
                            response.raise_for_status()
                            data = response.json()
                        except Exception:
                            continue
                        answers = data.get("Answer") or []
                        results.extend(
                            item.get("data")
                            for item in answers
                            if item.get("type") == answer_type and item.get("data")
                        )
                        if results:
                            break
        finally:
            cls.state.resolving_doh = False
        return results

    @classmethod
    def patched_getaddrinfo(
        cls,
        host,
        port,
        family=0,
        type=0,
        proto=0,
        flags=0,
    ):
        if getattr(cls.state, "resolving_doh", False):
            return ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)
        if family not in (0, socket.AF_UNSPEC, socket.AF_INET, socket.AF_INET6):
            return ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)
        normalized_family = socket.AF_UNSPEC if family == 0 else family
        addresses = cls.resolve(host, normalized_family)
        if not addresses:
            return ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)
        random.shuffle(addresses)
        result = []
        socktype = type or socket.SOCK_STREAM
        protocol = proto or socket.IPPROTO_TCP
        for address in addresses:
            address_family = cls.address_family(address)
            if address_family == socket.AF_INET6:
                sockaddr = (address, port, 0, 0)
            else:
                sockaddr = (address, port)
            result.append((address_family, socktype, protocol, "", sockaddr))
        return result

    @staticmethod
    def is_ip(host):
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            return False

    @staticmethod
    def address_family(address):
        parsed = ipaddress.ip_address(address)
        return socket.AF_INET6 if parsed.version == 6 else socket.AF_INET

    @classmethod
    def matches_family(cls, address, family):
        if family in (0, socket.AF_UNSPEC):
            return True
        if not cls.is_ip(address):
            return family in (socket.AF_UNSPEC, 0)
        return cls.address_family(address) == family

    @staticmethod
    def query_types(family):
        if family == socket.AF_INET:
            return (("A", 1),)
        if family == socket.AF_INET6:
            return (("AAAA", 28),)
        return (("A", 1), ("AAAA", 28))

    @classmethod
    @contextmanager
    def resolver_patch(cls):
        with cls.patch_lock:
            if cls.patch_count == 0:
                socket.getaddrinfo = cls.patched_getaddrinfo
            cls.patch_count += 1
        try:
            yield
        finally:
            with cls.patch_lock:
                cls.patch_count -= 1
                if cls.patch_count == 0:
                    socket.getaddrinfo = ORIGINAL_GETADDRINFO
