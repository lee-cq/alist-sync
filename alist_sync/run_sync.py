# coding: utf8
"""基础同步
[dir1, dir2, dir3]

各个Dir分别成为源目录，并Copy至其他目录

"""
import logging

from alist_sync.base_sync import SyncBase
from alist_sync.checker import check_dir
from alist_sync.job_copy import CopyJob
from alist_sync.config import AlistServer

logger = logging.getLogger("alist-sync.run-sync")


class Sync(SyncBase):
    def __init__(self, alist_info: AlistServer, dirs: list[str] = None):
        super().__init__(alist_info, dirs)

    async def async_run(self):
        """异步运行"""
        await super().async_run()
        checker = await check_dir(*self.sync_dirs, client=self.client)
        copy_job = CopyJob.from_checker(
            self.sync_dirs,
            self.sync_dirs,
            checker,
        )

        await copy_job.start(self.client)
        logger.info("同步完成。")
