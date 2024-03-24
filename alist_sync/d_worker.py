import atexit
import datetime
import logging
import sys
import threading
import time
import traceback
from pathlib import Path
from queue import Queue, Empty
from typing import Literal, Any, Type

from pydantic import BaseModel, computed_field, Field
from pymongo.collection import Collection
from httpx import Client, TimeoutException, Timeout
from alist_sdk.path_lib import AbsAlistPathType, AlistPath

from alist_sync.config import create_config
from alist_sync.common import sha1, prefix_in_threads, transfer_speed
from alist_sync.err import WorkerError, RetryError
from alist_sync.thread_pool import MyThreadPoolExecutor
from alist_sync.version import __version__

sync_config = create_config()

WorkerType = ("delete", "copy")

# noinspection PyTypeHints,PyCompatibility
WorkerTypeModify = Literal[*WorkerType]

WorkerStatus = {
    "init": 9,  # 9
    "deleted": 2,  # 2
    "back-upped": 8,  # 8
    "downloaded": 5,  # 5
    "uploaded": 3,  # 3
    "copied": 2,  # 2
    "done": 0,  # 0
    "failed": 1,  # 1
}
# noinspection PyTypeHints,PyCompatibility
WorkerStatusModify = Literal[*WorkerStatus.keys()]

logger = logging.getLogger("alist-sync.worker")

downloader_client = Client(
    headers={
        "User-Agent": sync_config.ua
        or f"alist-sync/{__version__}/ Python {sys.version}"
    },
)


# noinspection PyTypeHints
class Worker(BaseModel):
    owner: str = sync_config.name
    group_name: str = None

    created_at: datetime.datetime = datetime.datetime.now()
    done_at: datetime.datetime | None = None
    type: WorkerTypeModify
    need_backup: bool
    backup_dir: AbsAlistPathType | None = None

    relative_path: str | None = None
    source_path: AbsAlistPathType | None = None
    target_path: AbsAlistPathType  # 永远只操作Target文件，删除也是作为Target
    status: WorkerStatusModify = "init"
    error_info: str | None = None

    # 私有属性
    workers: "Workers | None" = Field(None, exclude=True)
    collection: Collection | None = Field(None, exclude=True)
    upload_id: str | None = Field(None, exclude=True)

    model_config = {
        "arbitrary_types_allowed": True,
        "excludes": {"workers", "collection", "tmp_file"},
    }

    def __init__(self, **data: Any):
        super().__init__(**data)
        # logger.info(
        #     f"Worker[{self.short_id}] Created: " f"{self.model_dump_json(indent=2)}"
        # )

    def __repr__(self):
        return f"<Worker {self.type}: {self.source_path} -> {self.target_path}>"

    def __lt__(self, other):
        return self.priority < other.priority

    @property
    def priority(self) -> int:
        return WorkerStatus[self.status]

    @computed_field()
    @property
    def file_size(self) -> int | None:
        if self.source_path is None:
            return None
        return self.source_path.stat().size

    @computed_field(return_type=str, alias="_id")
    @property
    def id(self) -> str:
        return sha1(f"{self.type}{self.source_path}{self.created_at}")

    @property
    def short_id(self) -> str:
        return self.id[:8]

    @computed_field()
    @property
    def tmp_file(self) -> Path:
        return sync_config.cache_dir.joinpath(f"download_tmp_{sha1(self.source_path)}")

    def update(self, **field: Any):
        if (status := field.get("status", "init")) not in WorkerStatus:
            raise ValueError(f"Unknown Status: {status}, allow: {WorkerStatus}.")
        if field:
            if field.keys() | self.__dict__.keys() != self.__dict__.keys():
                raise KeyError()
            self.__dict__.update(field)

        if self.status in ["done", "failed"]:
            logger.info(f"Worker[{self.short_id}] is {self.status}.")
            self.done_at = datetime.datetime.now()
            sync_config.handle.create_log(self)
            if self.status == "done":
                logger.info(
                    f"Worker[{self.short_id}] "
                    f"{self.source_path} -> {self.target_path} "
                    f"平均传输速度: "
                    f"{transfer_speed(self.file_size, self.done_at, self.created_at)}"
                )
            self.tmp_file.unlink(missing_ok=True)
            return sync_config.handle.delete_worker(self.id)

        return sync_config.handle.update_worker(self, *field.keys())

    def backup(self):
        """备份"""
        if self.backup_dir is None:
            raise ValueError("Need Backup, But no Dir.")
        _backup_file = self.target_path
        _target_name = (
            f"{sha1(_backup_file.as_posix())}_"
            f"{int(_backup_file.stat().modified.timestamp())}.history"
        )
        _backup_target = self.backup_dir.joinpath(_target_name)
        _backup_target_json = self.backup_dir.joinpath(_target_name + ".json")
        _old_info = _backup_file.stat().model_dump_json()

        assert (
            not _backup_target.exists() and not _backup_target_json.exists()
        ), "备份目标冲突"

        _backup_file.rename(_backup_target)
        assert _backup_target.exists()
        _backup_target_json.write_text(_old_info)
        assert _backup_target_json.re_stat() is not None

        self.update(status="back-upped")
        logger.info(f"Worker[{self.short_id}] Backup Success.")

    def __retry(
        self,
        retry: int,
        excepts: tuple[Type[Exception], ...],
        func,
        *args,
        **kwargs,
    ):
        while retry > 0:
            try:
                return func(*args, **kwargs)
            except excepts as _e:
                if retry <= 0:
                    logger.error(
                        f"Worker[{self.short_id}] Retry Error [{func.__name__}]: "
                        f"{type(_e)} - {_e}"
                    )
                    raise RetryError(f"Retry {func.__name__} Error.") from _e
                logger.warning(
                    f"Worker[{self.short_id}] {retry = } [{func.__name__}]: "
                    f"{type(_e)} - {_e}"
                )
                retry -= 1
                continue


class Workers:
    def __init__(self):
        self.thread_pool = MyThreadPoolExecutor(
            20,
            "worker_",
        )

        self.lockers: set[AlistPath] = set()

        atexit.register(self.__del__)

    def __del__(self):
        for i in sync_config.cache_dir.iterdir():
            if i.name.startswith("download_tmp_"):
                i.unlink(missing_ok=True)

    def release_lock(self, *items: AlistPath):
        for p in items:
            self.lockers.remove(p)

    def add_worker(self, worker: Worker, is_loader=False):
        if not is_loader and (
            worker.source_path in self.lockers or worker.target_path in self.lockers
        ):
            logger.warning(f"Worker[{worker.id}]中有路径被锁定.")
            return

        self.lockers.add(worker.source_path)
        self.lockers.add(worker.target_path)

        worker.workers = self
        self.thread_pool.submit_wait(worker.run)
        logger.info(f"Worker[{worker.id}] added to ThreadPool.")

    def run(self, queue: Queue):
        """"""
        # self.lockers |= sync_config.handle.load_locker()
        # for i in sync_config.handle.get_workers():
        #     self.add_worker(Worker(**i), is_loader=True)
        _started = False
        while True:
            if (
                queue.empty()
                and sync_config.daemon is False
                and not prefix_in_threads("checker_")
                and time.time() - sync_config.start_time > sync_config.timeout
            ):
                logger.info(
                    f"等待Worker执行完成, 排队中的数量: {self.thread_pool.work_qsize()}"
                )
                self.thread_pool.shutdown(wait=True, cancel_futures=False)
                logger.info(f"循环线程退出 - {threading.current_thread().name}")
                return

            try:
                _started = True
                self.add_worker(queue.get(timeout=3))
            except Empty:
                if _started:
                    continue
                logger.info(
                    f"Checkers: 空 Scaner 队列, 如果没有新的任务, "
                    f"{sync_config.timeout - (time.time() - sync_config.start_time):d}"
                    f"秒后退出"
                )

    def start(self, queue: Queue) -> threading.Thread:
        _t = threading.Thread(
            target=self.run,
            args=(queue,),
            name="workers_main",
        )
        _t.start()
        logger.info("Worker Main Thread Start...")
        return _t


if __name__ == "__main__":
    from alist_sdk import AlistPath, login_server

    _w = Worker.model_validate(
        {
            "owner": "test",
            "created_at": "2024-03-01T15:59:37.222074",
            "done_at": "2024-03-01T15:59:42.568337",
            "type": "copy",
            "need_backup": False,
            "backup_dir": None,
            "source_path": "http://localhost:5244/onedrive/HuaZhang.sqlite",
            "target_path": "http://localhost:5244/Drive-New/HuaZhang.sqlite",
            "status": "init",
            "error_info": "",
            "id": "228e0fa2906875ea18c83f4aa4c40aaa84d1d47e",
        }
    )

    for s in sync_config.alist_servers:
        login_server(**s.dump_for_alist_path())

    print(_w.tmp_file, type(_w.source_path), _w.target_path)
    _w.run()
