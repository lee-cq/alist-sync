import atexit
import datetime
import logging
import threading
from pathlib import Path
from queue import Queue
from typing import Literal, Any

from pydantic import BaseModel, computed_field, Field
from pymongo.collection import Collection
from alist_sdk.path_lib import AbsAlistPathType, AlistPath

from alist_sync.config import create_config
from alist_sync.common import sha1
from alist_sync.thread_pool import MyThreadPoolExecutor

sync_config = create_config()

WorkerType = Literal["delete", "copy"]
WorkerStatus = Literal[
    "init",
    "deleted",
    "back-upping",
    "back-upped",
    "downloading",
    "uploading",
    "copied",
    "done",
    "failed",
]

logger = logging.getLogger("alist-sync.worker")


class Worker(BaseModel):
    owner: str = sync_config.runner_name
    created_at: datetime.datetime = datetime.datetime.now()
    type: WorkerType
    need_backup: bool
    backup_dir: AbsAlistPathType | None = None

    source_path: AbsAlistPathType | None = None
    target_path: AbsAlistPathType  # 永远只操作Target文件，删除也是作为Target
    status: WorkerStatus = "init"
    error_info: BaseException | None = None

    # 私有属性
    workers: "Workers | None" = Field(None, exclude=True)
    collection: Collection | None = Field(None, exclude=True)

    model_config = {
        "arbitrary_types_allowed": True,
        "excludes": {
            "workers",
            "collection",
        },
    }

    def __init__(self, **data: Any):
        super().__init__(**data)
        logger.info(f"Worker[{self.id}] Created: {self.__repr__()}")

    def __repr__(self):
        return f"<Worker {self.type}: {self.source_path} -> {self.target_path}>"

    @computed_field(return_type=str, alias="_id")
    @property
    def id(self) -> str:
        return sha1(f"{self.type}{self.source_path}{self.created_at}")

    @property
    def tmp_file(self) -> Path:
        return sync_config.cache_dir.joinpath(f"download_tmp_{sha1(self.source_path)}")

    def update(self, *field: Any):
        if self.status == "done" and self.collection is not None:
            return self.collection.delete_one({"_id": self._id})
        return sync_config.handle.update_worker(self, *field)

    def backup(self):
        """备份"""
        if self.backup_dir is None:
            raise ValueError("Need Backup, But no Dir.")
        _backup_file = self.source_path if self.type == "delete" else self.target_path

    def downloader(self):
        """HTTP多线程下载"""

    def upload(self):
        """上传到alist"""

    def copy_type(self):
        """复制任务"""

    def delete_type(self):
        """删除任务"""

    def run(self):
        """启动Worker"""
        logger.info(f"worker[{self._id}] 已经安排启动.")
        try:
            if self.need_backup:
                self.backup()

            if self.type == "copy":
                self.copy_type()
            elif self.type == "delete":
                self.delete_type()
        except Exception as _e:
            self.error_info = _e
            self.status = "failed"
            self.update()
            logger.error(f"worker[{self._id}] 出现错误: {_e}")


class Workers:

    def __init__(self):
        self.thread_pool = MyThreadPoolExecutor(
            5,
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

    def add_worker(self, worker: Worker):
        if worker.source_path in self.lockers or worker.target_path in self.lockers:
            logger.warning(f"Worker {worker} 有路径被锁定.")
            return

        self.lockers.add(worker.source_path)
        self.lockers.add(worker.target_path)

        worker.workers = self
        self.thread_pool.submit(worker.run)
        logger.info(f"Worker[{worker.id}] added to ThreadPool.")

    def run(self, queue: Queue):
        """"""
        self.lockers |= sync_config.handle.load_locker()
        for i in sync_config.handle.get_workers():
            self.add_worker(Worker(**i))

        while True:
            self.add_worker(queue.get())

    def start(self, queue: Queue) -> threading.Thread:
        _t = threading.Thread(target=self.run, args=(queue,))
        _t.start()
        logger.info("Worker Main Thread Start...")
        return _t


if __name__ == "__main__":
    from alist_sdk import AlistPath

    _w = Worker(
        type="copy",
        need_backup=False,
        source_path=AlistPath("http://local:/sc"),
        target_path="http://target_path",
    )
    print(_w.tmp_file, type(_w.source_path), _w.target_path)
    print()
    print(_w.model_dump())
    print(_w.model_dump(mode="json"))
