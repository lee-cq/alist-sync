#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : d_checker.py
@Author     : LeeCQ
@Date-Time  : 2024/2/25 21:17

"""
import fnmatch
import logging
import threading
import time
from queue import Queue, Empty
from typing import Iterator
from functools import lru_cache

from alist_sdk import AlistPath, RawItem, AlistPathType
from pydantic import BaseModel

from alist_sync.config import create_config, SyncGroup
from alist_sync.d_worker import Worker
from alist_sync.thread_pool import MyThreadPoolExecutor
from alist_sync.common import prefix_in_threads


logger = logging.getLogger("alist-sync.d_checker")
sync_config = create_config()


class SyncRawItem(BaseModel):
    path: AlistPathType | None
    stat: RawItem

    def exists(self):
        return self.stat is not None

    def is_file(self):
        return not self.stat.is_dir

    def is_dir(self):
        return self.stat.is_dir


class Checker:
    def __init__(self, sync_group: SyncGroup, scaner_queue: Queue, worker_queue: Queue):
        self.sync_group: SyncGroup = sync_group
        self.worker_queue = worker_queue
        self.scaner_queue: Queue[AlistPath] = scaner_queue

        self.conflict: set = set()
        self.pool = MyThreadPoolExecutor(10)
        self.main_thread = threading.Thread(
            target=self.main,
            name=f"checker_main[{self.sync_group.name}-{self.__class__.__name__}]",
        )

    @lru_cache(64)
    def split_path(self, path: AlistPath) -> tuple[AlistPath, str]:
        """将Path切割为sync_dir和相对路径"""
        for sr in self.sync_group.group:
            try:
                return sr, path.relative_to(sr)
            except ValueError:
                pass
        raise ValueError()

    def get_backup_dir(self, path) -> AlistPath:
        return self.split_path(path)[0].joinpath(self.sync_group.backup_dir)

    @lru_cache(40_000)
    def get_stat(self, path: AlistPath) -> SyncRawItem:
        try:
            stat = path.re_stat()
        except FileNotFoundError:
            stat = None

        return SyncRawItem(path=path, stat=stat)

    def checker(
        self,
        source_stat: SyncRawItem,
        target_stat: SyncRawItem,
    ) -> "Worker|None":
        raise NotImplementedError

    def ignore(self, relative_path) -> bool:
        for _i in self.sync_group.blacklist:
            if fnmatch.fnmatchcase(relative_path, _i):
                logger.debug("Ignore: %s, [matched: %s]", relative_path, _i)
                return True
        return False

    def checker_every_dir(self, path) -> Iterator[Worker | None]:
        _sync_dir, _relative_path = self.split_path(path)
        logger.debug(f"Checking [{_relative_path}] in {self.sync_group.group}")
        for _sd in self.sync_group.group:
            _sd: AlistPath
            if _sd == _sync_dir:
                continue
            target_path = _sd.joinpath(_relative_path)
            yield self.checker(self.get_stat(path), self.get_stat(target_path))

    def _t_checker(self, path):
        try:
            for _c in self.checker_every_dir(path):
                if _c:
                    self.worker_queue.put(_c)
        except Exception as _e:
            logger.error("Checker Error: ", exc_info=_e)

    def main(self):
        """"""
        logger.info(f"Checker Started - name: {self.main_thread.name}")
        _started = False
        while True:
            if (
                self.scaner_queue.empty()
                and sync_config.daemon is False
                and not prefix_in_threads("scaner_")
                and time.time() - sync_config.start_time > sync_config.timeout
            ):
                logger.info(f"循环线程退出 - {self.main_thread.name}")
                break

            try:
                _started = True
                path = self.scaner_queue.get(timeout=3)
                self.pool.submit(self._t_checker, path)
            except Empty:
                if _started:
                    continue
                logger.info(
                    f"Checkers: 空 Scaner 队列, 如果没有新的任务, "
                    f"{sync_config.timeout - (time.time() - sync_config.start_time):d}"
                    f"秒后退出"
                )

    def start(self) -> threading.Thread:
        self.main_thread.start()
        return self.main_thread


class CheckerCopy(Checker):
    """"""

    def checker(
        self, source_stat: SyncRawItem, target_stat: SyncRawItem
    ) -> "Worker|None":
        if not target_stat.exists():
            logger.info(
                f"Checked: [COPY] {source_stat.path.as_uri()} -> {target_stat.path.as_uri()}"
            )
            return Worker(
                type="copy",
                need_backup=False,
                source_path=source_stat.path,
                target_path=target_stat.path,
            )
        logger.info(f"Checked: [JUMP] {source_stat.path.as_uri()}")
        return None


class CheckerMirror(Checker):
    """"""

    def checker(
        self, source_stat: SyncRawItem, target_stat: SyncRawItem
    ) -> "Worker|None":
        # _main = self.sync_group.group[0]
        # # target如果是主存储器 - 且target不存在，source存在，删除source
        # if target_stat == _main and not target_stat.exists() and source_stat.exists():
        #     return Worker(
        #         type="delete",
        #         need_backup=self.sync_group.need_backup,
        #         backup_dir=self.get_backup_dir(source_stat.path),
        #         target_path=source_stat.path,
        #     )
        # if not target_stat.exists():
        #     return Worker(
        #         type="copy",
        #         need_backup=False,
        #         source_path=source_stat.path,
        #         target_path=target_stat.path,
        #     )
        return None


class CheckerSync(Checker):
    """"""


class CheckerSyncIncr(Checker):
    """"""


def get_checker(type_: str) -> type[Checker]:
    return {
        "copy": CheckerCopy,
        "mirror": CheckerMirror,
        "sync": CheckerSync,
        "sync-incr": CheckerSyncIncr,
    }[type_]
