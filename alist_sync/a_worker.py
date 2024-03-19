"""

"""

import asyncio
import logging
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


logger = logging.getLogger("alist-sync.a_worker")


class TempFile(BaseModel):
    local_path: Path
    remote_path: AlistPathType
    status: Literal["init", "downloading", "downloaded", "failed", "removed"] = "init"
    refer_times: int = 1


class TempFiles(BaseModel):
    pre_size: int = 0
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
        self.worker_queue = asyncio.PriorityQueue()
        self.tmp_files: TempFiles = TempFiles()

        self.sp_workers = asyncio.Semaphore(5)
        self.sp_downloader = asyncio.Semaphore(5)
        self.sp_uploader = asyncio.Semaphore(5)

    def clear_tmp_file(self):
        """清理临时文件"""
        # for fp in self.tmp_files:
        #     fp: Path

    def add_worker(self, worker: Worker):
        logger.debug("Added Worker: %s", worker.model_dump_json(indent=2))
        self.worker_queue.put_nowait((worker.priority, worker))

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
        logger.info("开始下载: %s", worker.source_path.as_uri())
        rt_code = await aria2c(
            make_aria2_cmd(
                remote=worker.source_path,
                local=worker.tmp_file,
            )
        )

        if rt_code != 0:
            worker.update(status="failed", error_info=f"下载失败, 返回码: {rt_code}")
            self.tmp_files.clear_file(worker.tmp_file)
            logger.error("下载失败, 返回码: %d", rt_code)
            raise DownloaderError(f"下载失败, 返回码: {rt_code}")
        worker.update(status="downloaded")

    async def uploader(self, worker: Worker):
        """"""
        assert worker.tmp_file.exists(), "临时文件不存在"
        assert (
            worker.tmp_file.stat().st_size == worker.source_path.stat().size
        ), f"临时文件大小不一致： {worker.tmp_file.stat().st_size} != {worker.source_path.stat().size}"

        def _upload():
            logger.debug("开始上传: %s", worker.target_path.as_uri())
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
                logger.error("上传失败: %d: %s", res.code, res.message)
                raise UploadError(f"{res.code}: {res.message}")

            logger.info("上传成功: %s", worker.target_path.as_uri())
            worker.update(status="copied")

        logger.info("开始上传: %s", worker.target_path.as_uri())
        await asyncio.to_thread(_upload)

    async def deleter(self, worker: Worker):
        """"""
        assert worker.status in [
            "init",
            "back-upped",
        ], f"Worker 状态异常, {worker.status}"
        assert worker.type == "delete", f"Worker 类型异常, {worker.type}"

        def _delete():
            worker.target_path.unlink()
            worker.update(status="deleted")

        logger.info("开始删除: %s", worker.target_path.as_uri())
        await asyncio.to_thread(_delete)

    async def re_checker(self, worker: Worker):
        """"""
        assert worker.status in ["deleted", "copied"], "Worker状态异常"

        def _recheck():
            if worker.type == "copy":
                if worker.source_path.stat().size == worker.target_path.re_stat().size:
                    worker.update(status="done")
                else:
                    worker.update(
                        status="failed", error_info="重新检查时文件大小不一致"
                    )
            elif worker.type == "delete":
                try:
                    worker.target_path.re_stat()
                    if worker.target_path.exists():
                        worker.update(
                            status="failed",
                            error_info=f"重新检查时文件依旧存在： {worker.target_path.as_uri()}",
                        )

                except FileNotFoundError:
                    worker.update(status="done")
            raise

        logger.info("开始重新检查: %s", worker.model_dump_json(indent=2))
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
        logger.error(f"不能选择合适的Action: \n {worker.model_dump_json(indent=2)}")
        raise StatusError(
            f"不能选择合适的Action: \n {worker.model_dump_json(indent=2)}"
        )

    async def _event(self, worker: Worker):
        """"""
        async with self.sp_workers:
            try:
                await self.action_selector(worker)(worker)
            finally:
                if worker.status not in ["done", "failed"]:
                    await self.worker_queue.put((worker.priority, worker))
                else:
                    await self.done(worker)

    async def a_main(self):
        logger.info("Worker Main Started.")
        while True:
            try:
                _p, worker = self.worker_queue.get_nowait()
                logger.debug("Worker Queue Size: %d", self.worker_queue.qsize())

                # noinspection PyAsyncCall
                asyncio.create_task(self._event(worker))
            except asyncio.QueueEmpty:
                logger.debug("Worker Queue is Empty. ")
                await asyncio.sleep(1)
                # TODO

    def mian(self):
        asyncio.run(self.a_main())
