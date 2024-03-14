"""

"""

import asyncio
import collections
import queue
from pathlib import Path
from typing import Literal, Any, Callable

from alist_sdk import AlistPath, AlistPathType
from pydantic import BaseModel

from alist_sync.d_worker import Worker

B = 1
KB = B * 1024
MB = KB * 1024
GB = MB * 1024


class TempFile(BaseModel):
    local_path: Path
    remote_path: AlistPathType
    status: Literal["init", "downloading", "downloaded", "failed", "removed"] = "init"
    refer_times: int = 0

    def __init__(self, **data: Any):
        super().__init__(**data)
        # TODO 自动调用Downloader


class TempFiles(BaseModel):
    tmp_files: dict[Path, int] = collections.defaultdict(int)

    def __del__(self):
        for fp in self.tmp_files.keys():
            fp.unlink(missing_ok=True)

    def add_tmp(self, path: Path, remote_file: str | AlistPath):
        self.tmp_files[path] += 1

    def done_tmp(self, path: Path):
        self.tmp_files[path] -= 1
        # if self.tmp_files[path] <= 0:
        #     self.clear_file(path)

    def clear_file(self, path: Path):
        path.unlink()
        del self.tmp_files[path]

    def total_size(self):
        return sum(fp.stat().st_size for fp in self.tmp_files.keys() if fp.exists())

    def status(self) -> tuple[int, int, int, str]:
        """
        :return 总大小，总文件数，总引用数，message
        """
        _total_size = self.total_size()
        _files = len(self.tmp_files)
        _uses = sum(self.tmp_files.values())
        return (
            _total_size,
            _files,
            _uses,
            f"当前缓存了{_files} 个文件，占用空间{_total_size}, 被{_uses} Worker引用。",
        )

    def auto_clear(self):
        if self.total_size() < 10 * GB:
            return
        [self.clear_file(path) for path, t in self.tmp_files.items() if t <= 0]
        return self.auto_clear()


class Workers:
    def __init__(self):
        self.worker_queue = queue.PriorityQueue()
        self.tmp_files: dict[Path, int] = collections.defaultdict(int)

    def clear_tmp_file(self):
        for fp in self.tmp_files:
            fp: Path

    def add_worker(self, worker: Worker):
        self.worker_queue.put((worker.priority, worker))

    async def backup(self, worker: Worker):
        """"""

    async def downloader(self, worker: Worker):
        """"""

    async def uploader(self, worker: Worker):
        """"""

    async def deleter(self, worker: Worker):
        """"""

    async def re_checker(self, worker: Worker):
        """"""

    async def _event(self, func: Callable, worker: Worker):
        """"""
        try:
            await func(worker)
        finally:
            self.worker_queue.put((worker.priority, worker))

    async def a_main(self):
        while True:
            _p, worker = self.worker_queue.get(timeout=3)



    def mian(self):
        asyncio.run(self.a_main())
