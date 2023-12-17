#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : jobs.py
@Author     : LeeCQ
@Date-Time  : 2023/12/17 18:02

"""
import asyncio
import logging
from pathlib import PurePosixPath
from typing import Iterator

from alist_sync.models import BaseModel
from alist_sync.alist_client import AlistClient
from alist_sync.checker import Checker
from alist_sync.common import get_alist_client

logger = logging.getLogger("alist-sync.jobs")


class JobBase(BaseModel):
    @staticmethod
    def create_task(_s, _t, checker: Checker) -> Iterator[BaseModel]:
        raise NotImplementedError

    @classmethod
    def from_checker(cls, source, target, checker: Checker):
        """从Checker中创建Task"""
        _tasks = {}

        def _1_1(sp: PurePosixPath, tp: PurePosixPath):
            for _task in cls.create_task(sp, tp, checker):
                _tasks[_task.name] = _task

        def _1_n(sp, tps):
            sp = PurePosixPath(sp)
            _tps = [PurePosixPath(tp) for tp in tps]
            [_1_1(sp, tp) for tp in _tps if sp != tp]

        def _n_n(sps, tps):
            [_1_n(sp, tps) for sp in sps]

        if isinstance(source, str | PurePosixPath) and isinstance(
            target, str | PurePosixPath
        ):
            _1_1(source, target)
        elif isinstance(source, str | PurePosixPath) and isinstance(
            target, list | tuple
        ):
            _1_n(source, target)
        elif isinstance(source, list | tuple) and isinstance(target, list | tuple):
            _n_n(source, target)
        else:
            raise ValueError(f"source: {source} or target: {target} not support")

        self = cls(tasks=_tasks)
        self.save_to_cache()
        return cls(tasks=_tasks)

    async def start(self, client: AlistClient = None):
        """开始复制任务"""
        logger.info(f"[{self.__class__.__name__}] " f"任务开始。")
        client = client or get_alist_client()
        while self.tasks:
            _keys = [k for k in self.tasks.keys()]
            for t_name in _keys:
                task = self.tasks[t_name]
                _task_status = await task.check_status(client=client)

                if _task_status:
                    logger.info(
                        f"[{self.__class__.__name__}] 任务完成: {task.name = }",
                    )
                    self.done_tasks[task.name] = task
                    self.tasks.pop(task.name)
                else:
                    logger.debug(
                        f"[{self.__class__.__name__}] "
                        f"任务状态: {task.name=} -> {task.status=}"
                    )
            self.save_to_cache()
            await asyncio.sleep(1)
        logger.info(f"[{self.__class__.__name__}] " f"All Done.")
