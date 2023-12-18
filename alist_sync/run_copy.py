import logging

from alist_sync.base_sync import SyncBase
from alist_sync.checker import check_dir
from alist_sync.common import async_all_task_names
from alist_sync.job_copy import CopyJob
from alist_sync.models import AlistServer
from alist_sync.scanner import scan_dirs

logger = logging.getLogger("alist-sync.copy-to-target")


class Copy(SyncBase):
    def __init__(
        self, alist_info: AlistServer, source_path: str, targets_path: list[str]
    ):
        self.mode = "copy"
        self.source_path = source_path
        self.targets_path = targets_path

        super().__init__(alist_info, [source_path, *targets_path])

    async def async_run(self):
        """异步运行"""
        await super().async_run()
        checker = await check_dir(*self.sync_dirs, client=self.client)
        copy_job = CopyJob.from_checker(self.source_path, self.targets_path, checker)
        await copy_job.start(self.client)
        logger.info("当前全部的Task %s", async_all_task_names())

        logger.info("复制完成。")
