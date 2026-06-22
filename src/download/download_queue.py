import queue
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import httpx

from mirrors.mirror_manager import MirrorManager
from services.http_config_service import HttpConfigService
from utils.dns_utils import DnsUtils
from utils.locker import Locker


class DownloadCancelled(Exception):
    pass


class DownloadQueue:
    try_times = 4
    connection_timeout = 30
    read_timeout = 5
    accept = "text/html, image/gif, image/jpeg, *; q=.2, */*; q=.2"
    accept_language = "zh_CN"
    pragma = "no-cache"
    connection = "keep-alive"
    accept_encoding = "br, gzip, deflate"

    def __init__(self):
        self.task_started = []
        self.task_progressed = []
        self.task_finished = []
        self._cancelled = threading.Event()
        self._client_pool = queue.Queue()
        self._task_queue = None

    def cancel(self):
        self._cancelled.set()
        if self._task_queue is not None:
            self._task_queue.shutdown(immediate=True)

    def download(self, tasks):
        task_list = list(tasks)
        if not task_list:
            return
        workers = min(len(task_list), HttpConfigService.thread)
        task_queue = queue.Queue()
        self._task_queue = task_queue
        for file in task_list:
            task_queue.put(file)
        while self._client_pool.qsize() < workers:
            self._client_pool.put(self._new_client())
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(self._download_worker, task_queue) for _ in range(workers)
            ]
            pending = set(futures)
            try:
                while pending:
                    done, pending = wait(
                        pending, timeout=0.2, return_when=FIRST_COMPLETED
                    )
                    for future in done:
                        future.result()
                    if self._cancelled.is_set():
                        raise DownloadCancelled("下载已取消")
            except KeyboardInterrupt, DownloadCancelled:
                self.cancel()
                for future in pending:
                    future.cancel()
                wait(futures)
                raise DownloadCancelled("下载已取消") from None
            except Exception:
                self.cancel()
                for future in pending:
                    future.cancel()
                wait(futures)
                raise
            finally:
                self._task_queue = None
                self._close_clients()

    def _download_worker(self, task_queue):
        while not self._cancelled.is_set():
            try:
                file = task_queue.get_nowait()
            except queue.Empty, queue.ShutDown:
                return
            self._download_one(file)

    def _download_one(self, file):
        self._throw_if_cancelled()
        with Locker.acquire_or_wait(file.local_path):
            self._throw_if_cancelled()
            if file.validate():
                self._emit(self.task_finished, file)
                return
            self._emit(self.task_started, file)
            self._download_file(file)
            self._throw_if_cancelled()
            if not file.unreachable and not file.validate_temp_and_apply():
                raise RuntimeError(
                    f"文件校验失败: {file.urls[0] if file.urls else file.local_path}"
                )
            self._emit(self.task_finished, file)

    def _download_file(self, file):
        if not file.urls:
            raise RuntimeError(
                f"文件 {file.display_name or file.local_path} 无Url，无法下载"
            )

        uri_list = list(MirrorManager.get_urls(file.urls))
        last_error = None
        headers = {
            "Accept": self.accept,
            "Accept-Language": self.accept_language,
            "Pragma": self.pragma,
            "Connection": self.connection,
            "Accept-Encoding": self.accept_encoding,
            "User-Agent": HttpConfigService.user_agent,
        }
        for attempt in range(1, self.try_times + 1):
            self._throw_if_cancelled()
            uri = uri_list[min(len(uri_list), attempt) - 1]
            client = self._client_pool.get()
            replace_client = False
            try:
                with DnsUtils.resolving(HttpConfigService.proxy is None):
                    with client.stream("GET", uri, headers=headers) as rsp:
                        rsp.raise_for_status()
                        size = (
                            int(rsp.headers.get("content-length") or file.size or 0)
                            or None
                        )
                        if size and size != file.size:
                            file.with_size(size)
                        Path(file.local_temp_path).parent.mkdir(
                            parents=True, exist_ok=True
                        )
                        received = 0
                        with open(file.local_temp_path, "wb") as fp:
                            for chunk in rsp.iter_bytes(1024 * 1024):
                                self._throw_if_cancelled()
                                if not chunk:
                                    continue
                                fp.write(chunk)
                                received += len(chunk)
                                self._emit(
                                    self.task_progressed,
                                    file,
                                    {
                                        "total": size,
                                        "received": received,
                                        "progressed": len(chunk),
                                    },
                                )
                return
            except httpx.HTTPStatusError as ex:
                file.delete_temp()
                last_error = ex
                status = ex.response.status_code
                if attempt < len(uri_list):
                    continue
                # 400系状态码除429外全部视为unreachable
                if status == 429:
                    raise RuntimeError(
                        "下载请求太频繁，请稍后重试，或打开代理再试。"
                    ) from ex
                if status // 100 == 4:
                    if file.required:
                        raise RuntimeError(
                            f"文件下载失败（{status}）: {uri} ，请重试几次，或打开代理再试"
                        ) from ex
                    file.set_unreachable()
                    return
            except DownloadCancelled:
                file.delete_temp()
                raise
            except Exception as ex:
                file.delete_temp()
                last_error = ex
                replace_client = True
            finally:
                if replace_client:
                    client.close()
                    client = self._new_client()
                self._client_pool.put(client)
            if attempt < self.try_times:
                if self._cancelled.wait(2):
                    raise DownloadCancelled("下载已取消")
        raise RuntimeError(
            f"文件下载失败: {uri_list[-1]} ，请重试几次，或打开代理再试"
        ) from last_error

    def _throw_if_cancelled(self):
        if self._cancelled.is_set():
            raise DownloadCancelled("下载已取消")

    @staticmethod
    def _emit(listeners, *args):
        for listener in listeners:
            listener(*args)

    def _new_client(self):
        return httpx.Client(
            follow_redirects=True,
            max_redirects=3,
            http2=True,
            timeout=httpx.Timeout(self.connection_timeout, read=self.read_timeout),
            limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
            proxy=HttpConfigService.proxy,
            trust_env=False,
        )

    def _close_clients(self):
        while True:
            try:
                client = self._client_pool.get_nowait()
            except queue.Empty, queue.ShutDown:
                return
            client.close()
