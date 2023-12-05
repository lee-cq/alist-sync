import asyncio
import logging
import os
from pathlib import PurePosixPath

from alist_sdk import Item, Task

from .base_sync import SyncBase
from .models import AlistServer, SyncDir, CopyTask

logger = logging.getLogger("alist-sync.copy-to-target")


class CopyToTarget(SyncBase):

    def __init__(self, alist_info: AlistServer, source_path: str, targets_path: list[str]):
        self.mode = 'copy'
        self.source_path = source_path
        self.targets_path = targets_path

        super().__init__(alist_info, [source_path, *targets_path])

    async def async_run(self):
        """异步运行"""
        await super().async_run()

        # 创建复制列表
        if not self.sync_task.copy_tasks:
            await self.create_copy_list()
            self.save_to_cache()
        else:
            logger.info(f"一件从缓存中找到 %d 个 CopyTask",
                        len(self.sync_task.copy_tasks))

        # 复制文件
        await self.copy_files()

    def create_copy_task(self, source: SyncDir, target: SyncDir):
        """通过比对源与目标到差异，创建复制列表"""
        for item in source.items:
            item: Item
            copy_path = item.full_name.relative_to(source.base_path)
            name = copy_path.name
            if target.in_items(copy_path):
                # 目标存在，判断是否需要更新
                logger.debug("[%s -> %s] %s: 目标存在",
                             source.base_path, target.base_path, copy_path)
                continue

            task = CopyTask(
                copy_name=name,  # 需要复制到文件名
                copy_source=PurePosixPath(source.base_path).joinpath(
                    copy_path.parent),  # 需要复制的源文件夹
                copy_target=PurePosixPath(target.base_path).joinpath(
                    copy_path.parent),  # 需要复制到的目标文件夹
            )
            self.sync_task.copy_tasks[task.name] = task
            self.save_to_cache()
            logger.debug("[%s -> %s] %s: 已创建复制任务信息。",
                         source.base_path, target.base_path, copy_path)

    async def create_copy_list(self):
        source = self.sync_task.sync_dirs.get(self.source_path)

        for sync_target in (self.sync_task.sync_dirs.get(t) for t in self.targets_path):
            sync_target: SyncDir
            self.create_copy_task(
                self.sync_task.sync_dirs.get(self.source_path),
                sync_target
            )
            logger.info(
                "[%s -> %s] 复制任务信息全部创建完成。",
                source.base_path,
                sync_target.base_path
            )

    async def copy_files(self):
        """复制文件"""

        async def copy(task, *args, **kwargs):
            res = await self.client.copy(*args, **kwargs)
            if res.code == 200:
                task.status = "created"
                self.save_to_cache()
                logger.info("[%s] 复制任务已经在AList中创建。", task.name)
            else:
                logger.warning("[%s] 复制任务创建失败。message: [%d]%s",
                               task.name, res.code, res.message)

        async def create_copy():
            while True:
                if not self.sync_task.copy_tasks:
                    break
                for copy_task in self.sync_task.copy_tasks.values():
                    copy_task: CopyTask
                    if copy_task.status != 'init':
                        continue
                    asyncio.create_task(
                        copy(
                            copy_task,
                            src_dir=copy_task.copy_source.as_posix(),
                            dst_dir=copy_task.copy_target.as_posix(),
                            files=[copy_task.copy_name, ]
                        ),
                        name=f"{id(self)}_copy_{copy_task.copy_name}"
                    )
                await asyncio.sleep(5)

        asyncio.create_task(create_copy())

        await self.check_status()
        logger.info("复制完成。")

    async def check_status(self):
        """状态更新"""
        while True:
            await asyncio.sleep(1)
            task_done = await self.client.task_done('copy')
            await self.client.task_clear_done('copy')
            task_undone = await self.client.task_undone('copy')
            if not task_undone.data:
                break
            logger.info(f"等待复制完成, 剩余 %d ...", len(task_undone.data))

            for t in task_done.data or []:
                t: Task
                if t.name not in self.sync_task.copy_tasks:
                    continue
                if t.status == "":
                    logger.info("[%s] 复制任务已经完成。", t.name)
                    self.sync_task.copy_tasks[t.name].status = 'success'
                    self.sync_task.copy_tasks.pop(t.name)
                    self.save_to_cache()
                    continue

                if t.error:
                    self.sync_task.copy_tasks[t.name].status = 'failed'
                    self.sync_task.copy_tasks[t.name].message = t.error
                    self.save_to_cache()
                    continue

                if t.status == "getting src object":
                    self.sync_task.copy_tasks[t.name].status = 'getting src object'
                    self.save_to_cache()
                    continue
