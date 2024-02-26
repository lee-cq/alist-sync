#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : d_checker.py
@Author     : LeeCQ
@Date-Time  : 2024/2/25 21:17

"""
from queue import Queue
from pymongo.collection import Collection

from alist_sdk import AlistPath

from alist_sync.config import create_config, SyncGroup
from alist_sync.d_worker import Worker
from alist_sync.thread_pool import MyThreadPoolExecutor

sync_config = create_config()


class Checker:
    def __init__(self, sync_group: SyncGroup, scaner_queue: Queue, worker_queue: Queue):
        self.sync_group: SyncGroup = sync_group
        self.worker_queue = worker_queue
        self.scaner_queue: Queue[AlistPath] = scaner_queue

        self.locker: set = set()
        self.load_locker()

        self.conflict: set = set()
        self.pool = MyThreadPoolExecutor(10)

    def split_path(self, path) -> tuple[AlistPath, str]:
        """将Path切割为sync_dir和相对路径"""
        for sr in self.sync_group.group:
            try:
                return sr, path.relative_to(sr)
            except:
                pass
        raise ValueError()

    def release_lock(self, *items: AlistPath):
        for p in items:
            self.locker.remove(p)

    def load_locker(self):
        col: Collection = sync_config.mongodb.workers
        for doc in col.find({}, {"source_path": True, "target_path": True}):
            for p in doc.values():
                if not None:
                    self.locker.add(AlistPath(p))

    def checker(self, path) -> "Worker|None":
        """检查器"""
        raise NotImplemented

    def _t_checker(self, path):
        if path in self.locker:
            return
        if _c := self.checker(path):
            self.worker_queue.put(_c)

    def mian(self):
        """"""
        while True:
            path = self.scaner_queue.get()
            self._t_checker(path)


class CheckerCopy(Checker):
    """"""

    def checker(self, path) -> "Worker|None":
        _sg = self.sync_group.group.copy()
        _sync_dir, _relative_path = self.split_path(path)
        _sg.remove(_sync_dir)

        for _sd in _sg:
            _sd: AlistPath
            target_path = _sd.joinpath(_relative_path)

            if not target_path.exists() and target_path not in self.locker:
                self.locker.add(target_path)
                self.locker.add(path)
                return Worker(
                    type="copy",
                    need_backup=False,
                    source_path=path,
                    target_path=target_path,
                )


class CheckerMirror(Checker):
    """"""


class CheckerSync(Checker):
    """"""
