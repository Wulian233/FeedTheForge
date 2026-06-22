import threading

from rich.progress import (BarColumn, Progress, ProgressColumn, SpinnerColumn,
                           TextColumn, TimeRemainingColumn)
from rich.text import Text

from download.download_queue import DownloadCancelled, DownloadQueue
from global_style import console
from utils.data_size_utils import humanize


class FileDownloadService:
    min_size_of_showed_file = 0 * 1024
    max_showed_files = 10

    @staticmethod
    def download(hint, files, check_cache):
        files = list(files)
        if not files:
            return
        if check_cache:
            with console.status("[yellow bold]检查下载缓存[/yellow bold]"):
                if all(file.validate() for file in files):
                    return
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}", justify="left"),
            MyProgressColumn(),
            BarColumn(),
            TimeRemainingColumn(),
            transient=True,
        ) as progress:
            general = progress.add_task(hint, total=len(files), kind="general")
            bars = {}
            bars_lock = threading.Lock()
            max_showed_files = max(1, FileDownloadService.max_showed_files)
            queue = DownloadQueue()

            def refresh_visible_files():
                for index, task in enumerate(bars.values()):
                    progress.update(task, visible=index < max_showed_files)

            def started(file):
                with bars_lock:
                    bars[file] = progress.add_task(
                        (file.display_name or "file").replace(" ", "-"),
                        total=file.size or 1,
                        visible=False,
                        kind="file",
                    )
                    refresh_visible_files()

            def progressed(file, event):
                with bars_lock:
                    task = bars.get(file)
                    if task is None:
                        return
                    total = event.get("total")
                    if total:
                        progress.update(task, total=total)
                    progress.update(task, completed=event.get("received") or 0)

            def finished(file):
                with bars_lock:
                    task = bars.pop(file, None)
                    if task is not None:
                        progress.update(task, completed=file.size or 1)
                        progress.remove_task(task)
                        refresh_visible_files()
                    progress.advance(general)

            queue.task_started.append(started)
            queue.task_progressed.append(progressed)
            queue.task_finished.append(finished)
            try:
                queue.download(files)
            except KeyboardInterrupt:
                queue.cancel()
                raise DownloadCancelled("下载已取消") from None


class MyProgressColumn(ProgressColumn):
    # noinspection PyMethodMayBeStatic
    def render(self, task):
        kind = task.fields.get("kind")
        if kind == "general":
            return Text(f"{task.completed:.0f}/{task.total or 0:.0f}", style="yellow")
        return Text(
            f"{humanize(task.completed)}/{humanize(task.total or 0)}",
            style="white",
        )
