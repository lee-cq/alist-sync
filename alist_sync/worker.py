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
from alist_sync.task import task_status
from alist_sync.common import sha1
from alist_sync.config import sync_trace

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
        status: str = const.TransferStatus.init,
        start_time: datetime = datetime.now(),
        end_time: datetime | None = None,
        task: Optional[Task] | None = None,
    ):
        self.transfer_type = transfer_type
        self.source_path = source_path
        self.target_path = target_path
        self.backup_path = backup_path
        self.status = status
        self.start_time = start_time
        self.end_time = end_time
        self.task = task

        self.transfer_log: TransferLog | None = None

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
            try:
                if self.status == const.TransferStatus.init:
                    self.init()
                    self.backup()

                elif self.status == const.TransferStatus.backed_up:
                    self.exec_()

                elif self.status == const.TransferStatus.coped:
                    self.recheck_copy()

                elif self.status == const.TransferStatus.done:
                    self.done()
                    break

                elif self.status == const.TransferStatus.error:
                    self.error()
                    break

                else:
                    logger.error(
                        f"Unknown Worker.status: {self.status}, "
                        f"{const.TransferStatus.str()}"
                    )
                    raise ValueError(
                        f"Unknown Worker.status: {self.status}, "
                        f"{const.TransferStatus.str()}"
                    )
            except Exception as e:
                logger.exception(f"Worker Error: {e} {self}")
                self.status = const.TransferStatus.error
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

    def init(self):
        """"""
        self.transfer_log = TransferLog(
            transfer_type=self.transfer_type,
            source_path=self.source_path,
            target_path=self.target_path,
            backup_path=self.backup_path,
            status=self.status,
        )
        self.transfer_log.set_id()
        self.transfer_log.save()

    def check_copy(self) -> bool:
        """是否已经存在复制任务"""
        if self.task is not None:
            return True
        # TODO Task实例应该如何引入

    def backup(self):
        """"""
        # backup_path 为None 或 target_path 不存在时，不进行备份
        if not self.backup_path or not self.target_path.exists():
            self.status = const.TransferStatus.backed_up
            logger.info(f"Not Need Backup: {self.target_path}")
            return

        try:
            stat = self.target_path.re_stat().model_dump_json()
            _backup_path: AlistPathType = self.backup_path
            _backup_stat_path = _backup_path.with_suffix(".json")
            _backup_path.unlink(missing_ok=True)
            _backup_stat_path.unlink(missing_ok=True)

            self.target_path.rename(_backup_path)
            _backup_stat_path.write_text(stat)
            self.status = const.TransferStatus.backed_up
            logger.info(f"backed Up Success: {self}")
        except AlistError as _e:
            # TODO
            logger.error(f"Backup Error: {_e} {self}")

    def copy_file(self):
        """创建Copy任务"""
        if self.source_path.drive != self.target_path.drive:
            logger.error("尚未实现在多个实例间同步数据。\n" "建议： 将多个存储挂载到同一个实例下操作。")
            self.status = const.TransferStatus.error
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
        self.task = _t.data.tasks[0]
        self.status = const.TransferStatus.coping
        # 等待Copy Task 执行完成, 等待条件 [0 waiting, 1 running, 8 等待重试]
        while self.task is not None and self.task.state in [0, 1, 4, 5, 8]:
            time.sleep(1)
            self.task = task_status.get_task(self.task.id)

        self.status = const.TransferStatus.coped

    def recheck_copy(self):
        """复查 - target存在，大小一致,mtime < 2 min"""
        now = datetime.now().timestamp()
        if not self.target_path.exists():
            self.status = const.TransferStatus.error
            self.transfer_log.message = "Recheck Error: target not exists."
            return

        if self.source_path.stat().size != self.target_path.stat().size:
            self.status = const.TransferStatus.error
            self.transfer_log.message = "Recheck Error: size not match."
            return

        if (now - self.target_path.stat().modified.timestamp() < 120) or (
            self.source_path.stat().modified != self.target_path.stat().modified
        ):
            self.status = const.TransferStatus.error
            self.transfer_log.message = "Recheck Error: mtime not match."
            return

        self.status = const.TransferStatus.done

    def retry(self):
        """重试
        这个版本不考虑重试
        """

    def done(self):
        """完成 - 清理工作"""
        self.end_time = datetime.now()  # 结束时间
        logger.info(f"Task Done. {self}")
        self.transfer_log.save()

    def error(self):
        """错误"""
        logger.error(f"Task Error. {self.transfer_log.message} {self}")
        self.transfer_log.save()
