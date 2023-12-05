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

from .models import RemoveTask, SyncDir
from .run_copy import CopyToTarget

logger = logging.getLogger("alist-sync.mirror")


class Mirror(CopyToTarget):

    def __init__(self, alist_info,
                 source_path: str = None,
                 targets_path: list[str] = []
                 ):
        self.mode = 'mirrors'
        super().__init__(alist_info,
                         source_path=source_path,
                         targets_path=targets_path)

    async def async_run(self):
        await super().async_run()

        # 创建删除列表
        if not self.sync_task.remove_tasks:
            logger.info("创建删除列表")
            self.create_remove_list()
            self.save_to_cache()

        else:
            logger.info(
                f"一件从缓存中找到 %d 个 RemoveTask", len(self.sync_task.remove_tasks)
            )

        # 删除文件
        await self.remove_files()

    def create_remove_task(self, source_dir: SyncDir, target_dir: SyncDir):
        """source无，删除target中有的"""
        for item in target_dir.items:
            item: Item
            re_path = item.full_name.relative_to(target_dir.base_path)
            if source_dir.in_items(re_path):
                logger.debug("Jump: 源[%s]中存在 -- %s ",
                             source_dir.base_path, re_path)
                continue

            logger.info("Add：源[%s]中不存在 - %s，计划删除 ...",
                        source_dir.base_path, re_path)

            self.sync_task.remove_tasks.setdefault(
                str(item.full_name),  # str
                RemoveTask(full_path=item.full_name)
            )
            logger.info("添加RemoveTask：%s", item.full_name)

    def create_remove_list(self):
        for sync_target in self.scaned_targets_dir:
            sync_target: SyncDir
            self.create_remove_task(
                self.scaned_source_dir, sync_target)
            logger.info(
                "[%s -> %s] 删除任务信息全部创建完成。",
                self.scaned_source_dir.base_path,
                sync_target.base_path
            )

    async def _remove_file(self, full_path):
        """"""
        res = await self.client.remove(
            path=str(full_path.parent),
            names=[full_path.name, ]
        )
        if res.code == 200:
            self.sync_task.remove_tasks.get(str(full_path)).status = "removing"

    async def remove_files(self):
        tasks = [asyncio.create_task(self._remove_file(item.full_path))
                 for path, item in self.sync_task.remove_tasks.items()]
        await asyncio.gather(*tasks)
