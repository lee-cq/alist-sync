# coding: utf-8
"""镜像复制

source -> [target, ...]

1. Source 复制到 Target，若Target中没有，复制
2. 若Target已经存在，忽略。
3. 若Target有source无，删除。

"""
import asyncio
import logging

from alist_sdk import Item

from alist_sync.checker import Checker
from alist_sync.common import async_all_task_names
from alist_sync.job_copy import CopyJob
from alist_sync.job_remove import RemoveJob
from alist_sync.base_sync import SyncBase

logger = logging.getLogger("alist-sync.mirror")


class Mirror(SyncBase):
    def __init__(
        self, alist_info, source_path: str = None, targets_path: list[str] = None
    ):
        self.mode = "mirrors"
        self.source_path = source_path
        self.targets_path = [] if not targets_path else targets_path
        super().__init__(alist_info, [source_path, *targets_path])

    async def async_run(self):
        # 创建复制列表
        await super().async_run()

        checker = Checker.checker(*self.sync_job.sync_dirs.values())
        copy_job = CopyJob.from_checker(self.source_path, self.targets_path, checker)
        delete_job = RemoveJob.from_checker(
            self.source_path, self.targets_path, checker
        )

        await asyncio.gather(
            copy_job.start(self.client),
            delete_job.start(self.client),
        )
        logger.info("当前全部的Task %s", async_all_task_names())

        logger.info(f"{self.__class__.__name__}完成。")
