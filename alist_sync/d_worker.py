import atexit
import datetime
import logging
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
from alist_sync.common import sha1, prefix_in_threads
from alist_sync.err import WorkerError, RetryError
from alist_sync.thread_pool import MyThreadPoolExecutor
from alist_sync.version import __version__

sync_config = create_config()

WorkerType = ["delete", "copy"]
# noinspection PyTypeHints
WorkerTypeModify = Literal[*WorkerType]

WorkerStatus = [
    "init",
    "deleted",
    "back-upped",
    "downloaded",
    "uploaded",
    "copied",
    "done",
    "failed",
]
# noinspection PyTypeHints
WorkerStatusModify = Literal[*WorkerTypeModify]

logger = logging.getLogger("alist-sync.worker")

downloader_client = Client(
    headers={"User-Agent": sync_config.ua or f"alist-sync/{__version__}"}
)


# noinspection PyTypeHints
class Worker(BaseModel):
    owner: str = sync_config.name
    created_at: datetime.datetime = datetime.datetime.now()
    done_at: datetime.datetime | None = None
    type: WorkerTypeModify
    need_backup: bool
    backup_dir: AbsAlistPathType | None = None

    source_path: AbsAlistPathType | None = None
    target_path: AbsAlistPathType  # 永远只操作Target文件，删除也是作为Target
    status: WorkerStatusModify = "init"
    error_info: str | None = None

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
        logger.info(f"Worker[{self.short_id}] Created: {self.__repr__()}")

    def __repr__(self):
        return f"<Worker {self.type}: {self.source_path} -> {self.target_path}>"

    def __del__(self):
        try:
            self.tmp_file.unlink(missing_ok=True)
        finally:
            pass

    @computed_field(return_type=str, alias="_id")
    @property
    def id(self) -> str:
        return sha1(f"{self.type}{self.source_path}{self.created_at}")

    @property
    def short_id(self) -> str:
        return self.id[:8]

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

    def downloader(self):
        """HTTP多线程下载"""
        # download
        with self.tmp_file.open("wb") as _tmp:
            with downloader_client.stream(
                "GET",
                self.source_path.get_download_uri(),
                follow_redirects=True,
            ) as _res:
                logger.debug(
                    f"Worker[{self.short_id}] Downloading from {self.source_path}"
                )
                for i in _res.iter_bytes(chunk_size=1024 * 1024):
                    _tmp.write(i)
        assert (
            self.tmp_file.exists()
            and self.tmp_file.stat().st_size == self.source_path.stat().size
        ), "下载后文件大小不一致"
        self.update(status="downloaded")

    def uploader(self):
        import urllib.parse

        # upload
        with self.tmp_file.open("rb") as fs:
            res = self.target_path.client.verify_request(
                "PUT",
                "/api/fs/put",
                headers={
                    "As-Task": "false",
                    "Content-Type": "application/octet-stream",
                    "Last-Modified": str(
                        int(self.source_path.stat().modified.timestamp() * 1000)
                    ),
                    "File-Path": urllib.parse.quote(str(self.target_path.as_posix())),
                },
                content=fs,
                timeout=Timeout(300, read=300, write=300, connect=300),
            )

        assert res.code == 200
        logger.info(
            f"Worker[{self.short_id}] Upload File "
            f"[{self.target_path}] [{res.code}]{res.message}."
        )
        self.update(status="uploaded")

    def copy_type(self):
        """复制任务"""
        logger.debug(f"Worker[{self.short_id}] Start Copping")
        if self.status not in ["downloaded", "uploaded"]:
            self.__retry(
                3,
                (TimeoutException, AssertionError),
                self.downloader,
            )

        if self.status != "uploaded":
            self.target_path.unlink(missing_ok=True)
            self.target_path.parent.mkdir(parents=True, exist_ok=True)
            self.__retry(
                3,
                (TimeoutException, AssertionError),
                self.uploader,
            )

        return self.update(status="copied")

    def delete_type(self):
        """删除任务"""
        self.target_path.unlink(missing_ok=True)
        assert not self.target_path.exists()
        self.update(status="deleted")

    def recheck_copy(self, retry=5, re_time=2):
        """再次检查当前Worker的结果是否符合预期。"""
        try:
            return (
                self.target_path.re_stat(retry=retry, timeout=re_time).size
                == self.source_path.re_stat().size
            )
        except FileNotFoundError:
            if retry > 0:
                return self.recheck_copy(retry=retry - 1, re_time=re_time)
            logger.error(
                f"Worker[{self.short_id}] Recheck Error: 文件不存在.({retry=})"
            )
            return False

    def recheck(self) -> bool:
        """再次检查当前Worker的结果是否符合预期。"""
        if self.type == "copy":
            return self.recheck_copy(retry=3, re_time=3)
        elif self.type == "delete":
            self.target_path.re_stat(retry=5, timeout=2)
            return not self.target_path.exists()
        else:
            raise ValueError(f"Unknown Worker Type {self.type}.")

    def run(self, is_retry=False):
        """启动Worker"""
        if is_retry is False:
            logger.info(f"worker[{self.short_id}] 已经开始工作.")
            self.update()

        try:
            if self.status in ["done", "failed"]:
                self.update()
                return
            if self.need_backup and self.status in ["init"]:
                self.backup()

            if self.type == "copy" and self.status in [
                "init",
                "back-upped",
                "downloaded",
                "uploaded",
            ]:
                self.copy_type()

            elif self.type == "delete" and self.status in ["init", "back-upped"]:
                self.delete_type()

            assert self.recheck()
            self.update(status=f"done")
            return
        except TimeoutException as _e:
            if is_retry:
                return self.__error_exec(_e)
            time.sleep(2)
            return self.__retry(
                3,
                (TimeoutException, AssertionError),
                self.run,
                True,
            )
        except Exception as _e:
            return self.__error_exec(_e)

    def __error_exec(self, _e: Exception):
        logger.error(
            f"Worker[{self.short_id}] 出现错误:: ({type(_e)}){_e}",
            exc_info=_e,
        )
        self.error_info = (
            f"Worker[{self.short_id}] 出现错误:: ({type(_e)}){_e}\n"
            f"{traceback.format_exc()}"
        )
        self.update(status="failed")
        if sync_config.debug:
            raise WorkerError from _e


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
                break

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
