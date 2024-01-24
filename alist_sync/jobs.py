#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : jobs.py
@Author     : LeeCQ
@Date-Time  : 2023/12/17 18:02

"""
import asyncio
import logging
import os
from pathlib import PurePosixPath
from typing import Iterator


from alist_sync.models import BaseModel
from alist_sync.alist_client import AlistClient
from alist_sync.checker import Checker
from alist_sync.common import get_alist_client, sha1

logger = logging.getLogger("alist-sync.jobs")


def get_need_backup_from_env() -> bool:
    _b = os.environ.get("ALIST_SYNC_BACKUP", "F").upper()
    if _b in ["Y", "YES", "TRUE", "OK"]:
        return True
    return False


class TaskBase(BaseModel):
    need_backup: bool = None
    backup_status: str = "init"
    backup_dir: PurePosixPath

    @property
    def client(self) -> AlistClient:
        return get_alist_client()

    async def backup(self, file: PurePosixPath):
        """备份， move应该不会创建Task,会等待完成后返回。
        包含创建元数据 sha1(file_path)_int(time.time()).history
        """
        if self.need_backup is None:
            self.need_backup = get_need_backup_from_env()

        if not self.need_backup:
            logger.info("Not Need Backup!")
            return True

        file_info = await self.client.get_item_info(file)
        if file_info.code == 404:
            logger.debug("目标文件不存在，无需备份")
            return True
        if file_info.code != 200:
            raise FileNotFoundError(
                f"BackupFileError: {file} -> {file_info.code}:{file_info.message}"
            )

        history_filename = (
            f"{sha1(str(file))}_{int(file_info.data.modified.timestamp())}.history"
        )
        if await self.backup_file_exist(history_filename) is True:
            raise FileExistsError(f"{history_filename}已经存在")

        logger.info("Backup File: {file}")
        res_bak = await self.client.move(
            src_dir=file.parent,
            dst_dir=self.backup_dir,
            files=file.name,
        )
        assert res_bak.code == 200, f"移动文件错误: {res_bak.message}"
        res_rename = await self.client.rename(
            history_filename, full_path=self.backup_dir.joinpath(file.name)
        )
        assert res_rename.code == 200, f"重命名错误: {res_rename.message}"
        res_meta = await self.client.upload_file_put(
            file_info.model_dump_json().encode(),
            path=self.backup_dir.joinpath(history_filename + ".json"),
        )
        assert res_meta.code == 200
        if (await self.backup_file_exist(history_filename)) is False:
            raise FileNotFoundError(f"{history_filename}")
        return True

    async def backup_file_exist(self, history_filename) -> bool:
        """验证Backup file 是否已经存在"""
        h_info = await self.client.get_item_info(
            self.backup_dir.joinpath(history_filename)
        )
        hj_info = await self.client.get_item_info(
            self.backup_dir.joinpath(history_filename + ".json")
        )
        if hj_info.code == 200 and h_info.code == 200:
            return True
        return False


class JobBase(BaseModel):
    """"""

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
        """开始任务"""
        logger.info(f"[{self.__class__.__name__}] " f"任务开始。")
        client = client or get_alist_client()
        while self.tasks:
            _keys = [k for k in self.tasks.keys()]
            for task_name in _keys:
                task = self.tasks[task_name]
                _task_status = await task.check_status()

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
