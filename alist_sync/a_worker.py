"""

"""

import asyncio
import queue
import urllib.parse
from pathlib import Path
from typing import Literal, Callable

from alist_sdk import AlistPath, AlistPathType
from httpx import Timeout
from pydantic import BaseModel

from alist_sync.d_worker import Worker
from alist_sync.downloader import make_aria2_cmd, aria2c
from alist_sync.err import *

B = 1
KB = B * 1024
MB = KB * 1024
GB = MB * 1024


class TempFile(BaseModel):
    local_path: Path
    remote_path: AlistPathType
    status: Literal["init", "downloading", "downloaded", "failed", "removed"] = "init"
    refer_times: int = 1


class TempFiles(BaseModel):
    pre_size = 0
    tmp_files: dict[Path, TempFile] = {}

    def __del__(self):
        for fp in self.tmp_files.keys():
            fp.unlink(missing_ok=True)

    def add_tmp(self, path: Path, remote_file: str | AlistPath):
        if path in self.tmp_files:
            self.tmp_files[path].refer_times += 1
        self.tmp_files[path] = TempFile(
            local_path=path,
            remote_path=remote_file,
        )

    def done_tmp(self, path: Path):
        assert path in self.tmp_files, f"没有找到path: {path}"
        self.tmp_files[path].refer_times -= 1
        # if self.tmp_files[path] <= 0:
        #     self.clear_file(path)

    def clear_file(self, path: Path):
        path.unlink()
        del self.tmp_files[path]

    def pre_total_size(self):
        return sum(_.remote_path.stat().size for _ in self.tmp_files.values())

    def total_size(self):
        return sum(fp.stat().st_size for fp in self.tmp_files.keys() if fp.exists())

    def status(self) -> tuple[int, int, int, str]:
        """
        :return 总大小，总文件数，总引用数，message
        """
        _total_size = self.total_size()
        _files = len(self.tmp_files)
        _uses = sum(_.refer_times for _ in self.tmp_files.values())
        return (
            _total_size,
            _files,
            _uses,
            f"当前缓存了{_files} 个文件，占用空间{_total_size}, 被{_uses} Worker引用。",
        )

    def auto_clear(self):
        if self.total_size() < 10 * GB:
            return
        [
            self.clear_file(path)
            for path, t in self.tmp_files.items()
            if t.refer_times <= 0
        ]
        return self.auto_clear()


# noinspection PyMethodMayBeStatic
class Workers:
    def __init__(self):
        self.worker_queue = queue.PriorityQueue()
        self.tmp_files: TempFiles = TempFiles()

        self.sp_workers = asyncio.Semaphore(5)
        self.sp_downloader = asyncio.Semaphore(5)
        self.sp_uploader = asyncio.Semaphore(5)

    def clear_tmp_file(self):
        for fp in self.tmp_files:
            fp: Path

    def add_worker(self, worker: Worker):
        self.worker_queue.put((worker.priority, worker))

    async def backup(self, worker: Worker):
        """"""

        await asyncio.to_thread(worker.backup)

    async def downloader(self, worker: Worker):
        """"""
        self.tmp_files.auto_clear()
        if self.tmp_files.pre_total_size() > 15 * GB:
            await asyncio.sleep(5)
            return

        self.tmp_files.add_tmp(worker.tmp_file, worker.source_path)
        await aria2c(make_aria2_cmd(worker.source_path, worker.tmp_file))

    async def uploader(self, worker: Worker):
        """"""
        assert worker.tmp_file.exists(), "临时文件不存在"
        assert (
            worker.tmp_file.stat().st_size == worker.source_path.stat().size
        ), f"临时文件大小不一致： {worker.tmp_file.stat().st_size} != {worker.source_path.stat().size}"

        def _upload():
            with worker.tmp_file.open("rb") as fs:
                res = worker.target_path.client.verify_request(
                    "PUT",
                    "/api/fs/put",
                    headers={
                        "As-Task": "true",
                        "Content-Type": "application/octet-stream",
                        "Last-Modified": str(
                            int(worker.source_path.stat().modified.timestamp() * 1000)
                        ),
                        "File-Path": urllib.parse.quote(
                            str(worker.target_path.as_posix())
                        ),
                    },
                    content=fs,
                    timeout=Timeout(300, read=300, write=300, connect=300),
                )

            if res.code != 200:
                worker.update(status="failed", error_info=f"{res.code}: {res.message}")
                raise UploadError(f"{res.code}: {res.message}")

            worker.update(status="uploaded")

        await asyncio.to_thread(_upload)

    async def deleter(self, worker: Worker):
        """"""
        assert worker.status in ["init", "back-upped"], f"Worker 状态异常, {worker.status}"
        assert worker.type == "delete", f"Worker 类型异常, {worker.type}"

        def _delete():
            res = worker.target_path.unlink()
            worker.update(status="deleted")

        await asyncio.to_thread(_delete)

    async def re_checker(self, worker: Worker):
        """"""
        assert worker.status in ["deleted", "copied"], "Worker状态异常"

        def _recheck():
            if worker.type == "copy":
                pass
            elif worker.type == "delete":
                pass
            raise

        await asyncio.to_thread(_recheck)

    async def done(self, worker):
        """"""

    def action_selector(self, worker: Worker) -> Callable:
        """WorkerStatus = {
        "init": 9,  # 9
        "deleted": 2,  # 2
        "back-upped": 8,  # 8
        "downloaded": 5,  # 5
        "uploaded": 3,  # 3
        "copied": 2,  # 2
        "done": 0,  # 0
        "failed": 1,  # 1
        }"""
        if worker.status == "init" and worker.need_backup is True:
            return self.backup
        if worker.type == "delete" and worker.status in ["init", "back-upped"]:
            return self.deleter
        if worker.type == "copy" and worker.status in ["init", "back-upped"]:
            return self.downloader
        if worker.status == "downloaded":
            return self.uploader
        if worker.status in ["copied", "deleted"]:
            return self.re_checker
        if worker.status in ["done", "failed"]:
            return self.done
        raise StatusError(f"不能选择合适的Action: \n {worker.model_dump_json(indent=2)}")

    async def _event(self, worker: Worker):
        """"""
        try:
            await self.action_selector(worker)(worker)
        finally:
            if worker.status not in ["done", "failed"]:
                self.worker_queue.put((worker.priority, worker))

    async def a_main(self):
        while True:
            try:
                with self.sp_workers:
                    _p, worker = self.worker_queue.get(timeout=3)
                    asyncio.create_task(self._event(worker))
            except queue.Empty:
                pass
                # TODO

    def mian(self):
        asyncio.run(self.a_main())
