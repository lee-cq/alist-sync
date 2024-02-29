#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : d_checker.py
@Author     : LeeCQ
@Date-Time  : 2024/2/25 21:17

"""
import logging
import threading
import time
from queue import Queue, Empty
from typing import Iterator

from alist_sdk import AlistPath

from alist_sync.config import create_config, SyncGroup
from alist_sync.d_worker import Worker
from alist_sync.thread_pool import MyThreadPoolExecutor
from common import prefix_in_threads

logger = logging.getLogger("alist-sync.d_checker")
sync_config = create_config()


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

    def split_path(self, path) -> tuple[AlistPath, str]:
        """将Path切割为sync_dir和相对路径"""
        for sr in self.sync_group.group:
            try:
                return sr, path.relative_to(sr)
            except ValueError:
                pass
        raise ValueError()

    def get_backup_dir(self, path) -> AlistPath:
        return self.split_path(path)[0].joinpath(self.sync_group.backup_dir)

    def checker(self, source_path: AlistPath, target_path: AlistPath) -> "Worker|None":
        raise NotImplementedError

    def checker_every_dir(self, path) -> Iterator[Worker | None]:
        _sync_dir, _relative_path = self.split_path(path)
        for _sd in self.sync_group.group:
            _sd: AlistPath
            if _sd == _sync_dir:
                continue
            target_path = _sd.joinpath(_relative_path)
            logger.debug(f"Check: {target_path} -> {path}")
            yield self.checker(path, target_path)

    def _t_checker(self, path):
        for _c in self.checker_every_dir(path):
            if _c:
                self.worker_queue.put(_c)

    def main(self):
        """"""
        logger.info(f"Checker Started - name: {self.main_thread.name}")
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
                self._t_checker(self.scaner_queue.get(timeout=3))
            except Empty:
                logger.debug("Checkers: 空 Scaner 队列.")
                pass

    def start(self) -> threading.Thread:
        self.main_thread.start()
        return self.main_thread


class CheckerCopy(Checker):
    """"""

    def checker(
        self,
        source_path: AlistPath,
        target_path: AlistPath,
    ) -> "Worker|None":
        if not target_path.exists():
            logger.debug(
                f"Checked: [COPY] {source_path.as_uri()} -> {target_path.as_uri()}"
            )
            return Worker(
                type="copy",
                need_backup=False,
                source_path=source_path,
                target_path=target_path,
            )
        logger.debug(f"Checked: [JUMP] {source_path.as_uri()}")
        return None


class CheckerMirror(Checker):
    """"""

    def checker(self, source_path: AlistPath, target_path: AlistPath) -> "Worker|None":
        _main = self.sync_group.group[0]
        # target如果是主存储器 - 且target不存在，source存在，删除source
        if target_path == _main and not target_path.exists() and source_path.exists():
            return Worker(
                type="delete",
                need_backup=self.sync_group.need_backup,
                backup_dir=self.get_backup_dir(source_path),
                target_path=source_path,
            )
        if not target_path.exists():
            return Worker(
                type="copy",
                need_backup=False,
                source_path=source_path,
                target_path=target_path,
            )
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
