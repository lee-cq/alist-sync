#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : worker.py
@Author     : LeeCQ
@Date-Time  : 2024/8/17 18:18
"""
import logging
import time
from typing import Optional
from datetime import datetime

from alist_sdk import AlistPathType, Task, AlistError

from alist_sync import const
from alist_sync.models import TransferLog
from alist_sync.task import copy_tasks

logger = logging.getLogger("alist-sync.worker")


class Worker:
    """工作函数"""

    #
    # transfer_type: str
    # source_path: AlistPathType
    # target_path: AlistPathType
    #
    # backup_path: AlistPathType | None = None
    #
    # status: str = const.TransferStatus.init
    # start_time: datetime = datetime.now()
    # end_time: datetime | None = None
    #
    # task: Optional[Task] | None = None

    def __init__(
        self,
        transfer_type: str,
        source_path: AlistPathType,
        target_path: AlistPathType,
        backup_path: AlistPathType | None = None,
        start_time: datetime = datetime.now(),
        end_time: datetime | None = None,
        task: Optional[Task] | None = None,
    ):
        self.transfer_type = transfer_type
        self.source_path = source_path
        self.target_path = target_path
        self.backup_path = backup_path
        self.start_time = start_time
        self.end_time = end_time
        self.task = task

        self.transfer_log = TransferLog(
            transfer_type=self.transfer_type,
            source_path=self.source_path,
            target_path=self.target_path,
            backup_path=self.backup_path,
            file_name=self.source_path.name,
            file_size=self.source_path.stat().size,
            mtime=self.source_path.stat().modified,
            status=const.TransferStatus.init,
        )
        self.transfer_log.set_id()
        self.transfer_log.save()

    def set_status(
        self,
        status: str,
        message: str | None = None,
    ):
        self.transfer_log.status = status
        if message:
            self.transfer_log.message = message
        self.transfer_log.save(only=self.transfer_log.dirty_fields)

    def __repr__(self) -> str:
        return f"Worker[{self.transfer_type}: {self.source_path} -> {self.target_path}]"

    def __str__(self) -> str:
        return f"Worker[{self.transfer_type}: {self.source_path} -> {self.target_path}]"

    def run(self):
        """开始运行
        1. 检查
        2. 备份
        3. 更新
        4. 核查
        5. 完成
        """
        logger.info(f"started Worker: {self}")
        while True:
            logger.debug(f"Worker.status: {self.transfer_log.status}")
            try:
                if self.transfer_log.status == const.TransferStatus.init:
                    self.backup()

                elif self.transfer_log.status == const.TransferStatus.backed_up:
                    self.exec_()

                elif self.transfer_log.status == const.TransferStatus.coped:
                    self.recheck_copy()
                    _recheck_count = 0
                    while (
                        self.transfer_log.status == const.TransferStatus.error
                        and _recheck_count < 3
                    ):
                        time.sleep(2)
                        self.recheck_copy()
                        _recheck_count += 1

                elif self.transfer_log.status == const.TransferStatus.done:
                    self.done()
                    break

                elif self.transfer_log.status == const.TransferStatus.error:
                    self.error()
                    break

                else:
                    logger.error(
                        f"Unknown Worker.status: {self.transfer_log.status}, "
                        f"{const.TransferStatus.str()}"
                    )
                    raise ValueError(
                        f"Unknown Worker.status: {self.transfer_log.status}, "
                        f"{const.TransferStatus.str()}"
                    )
            except Exception as e:
                logger.exception(f"Worker Error: {e} {self}")
                self.set_status(const.TransferStatus.error, str(e))
                break

    def exec_(self):
        if self.transfer_type == const.TransferType.copy:
            self.copy_file()
        elif self.transfer_type == const.TransferType.delete:
            raise NotImplemented  # TODO
        else:
            ValueError(
                f"Unknown Worker.t_type: {self.transfer_type}, "
                f"{const.TransferType.str()}"
            )

    def check_copy(self) -> bool:
        """是否已经存在复制任务"""
        if self.task is not None:
            return True
        # TODO Task实例应该如何引入

    def backup(self):
        """"""
        # backup_path 为None 或 target_path 不存在时，不进行备份
        if not self.backup_path or not self.target_path.exists():
            self.set_status(const.TransferStatus.backed_up)
            return

        try:
            stat = self.target_path.re_stat().model_dump_json()
            _backup_path: AlistPathType = self.backup_path
            _backup_stat_path = _backup_path.with_suffix(".json")
            _backup_path.unlink(missing_ok=True)
            _backup_stat_path.unlink(missing_ok=True)

            self.target_path.rename(_backup_path)
            _backup_stat_path.write_text(stat)
            self.set_status(const.TransferStatus.backed_up)
            logger.info(f"backed Up Success: {self}")
        except AlistError as _e:
            # TODO
            logger.error(f"Backup Error: {_e} {self}")

    def copy_file(self):
        """创建Copy任务"""
        if self.source_path.drive != self.target_path.drive:
            logger.error("尚未实现在多个实例间同步数据。\n" "建议： 将多个存储挂载到同一个实例下操作。")

            self.set_status(
                const.TransferStatus.error, "尚未实现在多个实例间同步数据。\n" "建议： 将多个存储挂载到同一个实例下操作。"
            )
            return
            # raise NotImplemented("尚未实现在多个实例间同步数据。\n" "建议： 将多个存储挂载到同一个实例下操作。")
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        _t = self.source_path.client.copy(
            self.source_path.parent.as_posix(),
            self.target_path.parent.as_posix(),
            [self.source_path.name],
        )
        if _t.code != 200:
            logger.error(
                f"Copy Error: [{_t.code}: {_t.message}] {str(self.source_path)} -> {str(self.target_path)}"
            )
            return None
        logger.info(f"Coping: ID[{_t.data.tasks[0].id}] -- {self}")

        assert _t.code == 200
        task_id = _t.data.tasks[0].id
        self.task = _t.data.tasks[0]
        self.set_status(const.TransferStatus.coping)
        # 等待Copy Task 执行完成, 等待条件 [0 waiting, 1 running, 8 等待重试]
        while True:
            time.sleep(2)
            task = copy_tasks.get_task(task_id)
            logger.debug(
                f"task status: [{task_id}]{self.target_path.name} "
                f": {task.state} : {task.progress:.2f}%"
            )
            if task.state not in [-1, 0, 1, 8]:
                break

        self.set_status(const.TransferStatus.coped)
        copy_tasks.remove_task(task_id)

    def recheck_copy(self):
        """复查 - target存在，大小一致,mtime < 2 min"""
        now = datetime.now().timestamp()
        if not self.target_path.exists():
            self.set_status(
                const.TransferStatus.error, "Recheck Error: target not exists."
            )
            return

        if self.source_path.stat().size != self.target_path.stat().size:
            self.set_status(
                const.TransferStatus.error, "Recheck Error: size not match."
            )
            return

        if (now - self.target_path.stat().modified.timestamp() < 120) or (
            self.source_path.stat().modified != self.target_path.stat().modified
        ):
            self.set_status(
                const.TransferStatus.error, "Recheck Error: mtime not match."
            )
            return

        self.set_status(const.TransferStatus.done)
        logger.info(f"Recheck Success: {self}")

    def retry(self):
        """重试
        这个版本不考虑重试
        """

    def done(self):
        """完成 - 清理工作"""
        self.end_time = datetime.now()  # 结束时间
        logger.info(f"Task Done. {self}")
        self.set_status(const.TransferStatus.done)
        self.transfer_log.save()

    def error(self):
        """错误"""
        logger.error(f"Task Error. {self.transfer_log.message} {self}")
        self.transfer_log.save()
