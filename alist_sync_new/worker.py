#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : worker.py
@Author     : LeeCQ
@Date-Time  : 2024/8/17 18:18
"""
import datetime
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
import pydantic

from alist_sdk import AlistPathType, Task, AlistError

from alist_sync_new import const
from alist_sync_new.task import task_status
from alist_sync_new.common import sha1

logger = logging.getLogger("alist-sync.worker")


class Worker(pydantic.BaseModel):
    """工作函数"""

    s_type: str
    source_path: AlistPathType
    target_path: AlistPathType

    need_backup: bool
    backup_dir: AlistPathType

    status: str = const.TransferStatus.init

    task: Optional[Task] = None

    def run(self):
        """开始运行
        1. 检查
        2. 备份
        3. 更新
        4. 核查
        5. 完成
        """

    @cached_property
    def backup_name(self) -> str:
        """待备份文件的posix_name sha1编码 + 待备份文件的mtime"""
        return (
            f"{sha1(self.target_path.as_posix())}_"
            f"{int(self.target_path.stat().modified.timestamp())}.history"
        )

    def check_backup(self) -> bool:
        """是否完成备份"""
        return (
            self.backup_dir.joinpath(self.backup_name)
            and self.backup_dir.joinpath(self.backup_name + ".json")
            and True
        )

    def check_copy(self) -> bool:
        """是否已经存在复制任务"""
        if self.task is not None:
            return True
        # TODO Task实例应该如何引入

    def backup(self):
        """"""
        try:
            stat = self.target_path.re_stat().model_dump_json()
            _backup_path: AlistPathType = self.backup_dir.joinpath(self.backup_name)
            _backup_stat_path = self.backup_dir.joinpath(self.backup_name)
            _backup_path.unlink(missing_ok=True)
            _backup_stat_path.unlink(missing_ok=True)

            self.target_path.rename(_backup_path)
            _backup_stat_path.write_text(stat)
            self.status = const.TransferStatus.backed_up
        except AlistError as _e:
            # TODO
            pass

    def copy_file(self):
        """创建Copy任务"""
        if self.source_path.drive != self.target_path.drive:
            logger.error("尚未实现在多个实例间同步数据。\n" "建议： 将多个存储挂载到同一个实例下操作。")
            self.status = const.TransferStatus.error
            return
            # raise NotImplemented("尚未实现在多个实例间同步数据。\n" "建议： 将多个存储挂载到同一个实例下操作。")

        _t = self.source_path.client.copy(
            self.source_path.parent, self.target_path.parent, [self.source_path.name]
        )
        assert _t.code == 200
        self.task = _t.data
        self.status = const.TransferStatus.coping
        # 等待Copy Task 执行完成
        while self.task.status == "":
            task_status.get_task(self.task.id)

    def recheck(self) -> bool:
        """复查 - target存在，且大小一致。"""
        now = datetime.datetime.now().timestamp()
        return (
            self.source_path.re_stat().size == self.target_path.re_stat().size
            and now - self.target_path.stat().modified.timestamp() < 120
        )

    def retry(self):
        """重试"""

    def done(self):
        """完成 - 清理工作"""


class WorkerPool(ThreadPoolExecutor):
    def __init__(self, max_workers=None):
        super().__init__(
            max_workers=max_workers,
            thread_name_prefix="sync-worker-",
            initializer=None,
            initargs=(),
        )
