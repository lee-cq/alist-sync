"""

"""

import asyncio
import logging
import time
import urllib.parse
from functools import lru_cache
from typing import Callable

from httpx import Timeout

from alist_sync.d_worker import Worker
from alist_sync.downloader import make_aria2_cmd, aria2c
from alist_sync.common import async_all_task_names, GB
from alist_sync.temp_files import TempFiles
from alist_sync.err import *


logger = logging.getLogger("alist-sync.a_worker")


LCU_UPLOAD_UNDONE: dict[str, callable] = {}  # URL, LCU缓存对象
LCU_UPLOAD_DONE: dict[str, callable] = {}  # URL, LCU缓存对象


def cached_upload(client, task_type: str = "undone", timeout: int = None) -> dict:
    if task_type not in ["undone", "done"]:
        raise ValueError(f"task_type 参数错误: {task_type}")

    lcu_dict = LCU_UPLOAD_UNDONE if task_type == "undone" else LCU_UPLOAD_DONE
    if timeout is None:
        timeout = 1 if task_type == "undone" else 5

    def maker_client_cache() -> callable:
        @lru_cache(maxsize=1)
        def _client_cache(_tmp_time: int) -> dict:
            _call = client.task_undone if task_type == "undone" else client.task_done
            res = _call("upload")
            if res.code != 200:
                raise RecheckError(f"获取上传任务失败: {res.code}: {res.message}")
            return {task.id: task for task in res.data}

        lcu_dict[client.base_url] = _client_cache
        return _client_cache

    return lcu_dict.get(client.base_url, maker_client_cache())(time.time() // timeout)


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

            assert res.data.task.id, "Task ID 不存在"
            logger.info(
                "上传成功[Task ID: %s]: %s",
                res.data.task.id,
                worker.target_path.as_uri(),
            )
            worker.update(status="copied", upload_id=res.data.task.id)

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
                assert worker.upload_id, "Upload ID 不存在"
                if worker.upload_id in cached_upload(
                    worker.target_path.client, "undone"
                ):
                    logger.debug("正在上传到后端存储: %s", worker.upload_id)
                    return
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

            else:
                raise ValueError(f"Worker 类型异常: {worker.type}")

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
                _action = self.action_selector(worker)
                worker_name = f"worker_{_action.__name__}_{worker.id}"
                asyncio.current_task().set_name(worker_name)
                logger.info("Awaiting Worker: %s", worker_name)
                await _action(worker)
            except Exception as e:
                logger.error("Worker Error: %s", e, exc_info=e)
                # worker.update(status="failed", error_info=str(e))
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
                asyncio.create_task(
                    self._event(worker), name=f"worker_None_{worker.id}"
                )
            except asyncio.QueueEmpty:
                workers_name: set = {
                    i for i in async_all_task_names() if i.startswith("worker_")
                }

                logger.debug(
                    f"Worker Queue is Empty. Tasks {len(workers_name)}",
                )
                await asyncio.sleep(1)
                # TODO 优雅退出

    def mian(self):
        asyncio.run(self.a_main())
