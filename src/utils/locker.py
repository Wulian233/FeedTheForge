import os
import time
from contextlib import suppress
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class Locker:
    def __init__(self, path, blocking=True, poll_interval=0.05):
        self.target = Path(path)
        self.lock_path = self._lock_path(self.target)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.lock_path, "a+b")
        self.is_new = self.lock_path.stat().st_size == 0
        self._locked = False
        try:
            self._acquire(blocking, poll_interval)
        except Exception:
            self._file.close()
            raise

    @staticmethod
    def _lock_path(path):
        if path.exists() and path.is_dir():
            return path.with_name(path.name + ".lock")
        return Path(str(path) + ".lock")

    @classmethod
    def try_acquire(cls, path):
        with suppress(BlockingIOError):
            return cls(path, blocking=False)
        return None

    @classmethod
    def acquire_or_wait(cls, path):
        return cls(path, blocking=True)

    def _acquire(self, blocking, poll_interval):
        if os.name == "nt":
            while True:
                try:
                    self._file.seek(0)
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
                    self._locked = True
                    return
                except OSError as ex:
                    if not blocking:
                        raise BlockingIOError(str(ex)) from ex
                    time.sleep(poll_interval)
        else:
            flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
            fcntl.flock(self._file.fileno(), flags)
            self._locked = True

    def release(self):
        if self._file.closed:
            return
        if self._locked:
            if os.name == "nt":
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            self._locked = False
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.release()

    def __del__(self):
        with suppress(Exception):
            self.release()
