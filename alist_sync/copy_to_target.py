import asyncio
import logging
from pathlib import PurePosixPath

from alist_sdk import AsyncClient, Item, Task
from .common import sha1_6
from .models import AlistServer, SyncDir, CopyTask, SyncTask
from .scan_dir import scan_dir
from .config import cache_dir

logger = logging.getLogger("alist-sync.copy-to-target")


class CopyToTarget:

    def __init__(self, alist_info: AlistServer, source_dir: str, target_path: list[str]):
        self.client = AsyncClient(timeout=30, **alist_info.model_dump())
        self.target_path = target_path
        self.source_dir = source_dir
        self.sync_task_cache_file = cache_dir / f"sync_task_{sha1_6(target_path)}_{sha1_6(target_path.sort())}.json"
        self.sync_task = SyncTask(
            alist_info=alist_info,
            sync_dirs=[],
            copy_tasks={}
        )
        self.load_from_cache()


    def load_from_cache(self):
        """从缓存中加载"""
        if not self.sync_task_cache_file.exists():
            return
        self.sync_task = SyncTask.model_validate_json(self.sync_task_cache_file.read_text())

    def save_to_cache(self):
        """保存到缓存中"""
        self.sync_task_cache_file.write_text(
            self.sync_task.model_dump_json(indent=2)
        )

    def run(self):
        asyncio.run(self.async_run())

    async def async_run(self):
        """异步运行"""
        if not self.sync_task.sync_dirs:
            await self.scans()
            self.save_to_cache()
        else:
            logger.info(f"一件从缓存中找到 %d 个 SyncDir", len(self.sync_task.sync_dirs))

        # 创建复制列表
        if not self.sync_task.copy_tasks:
            await self.create_copy_list()
            self.save_to_cache()
        else:
            logger.info(f"一件从缓存中找到 %d 个 CopyTask", len(self.sync_task.copy_tasks))

        # 复制文件
        await self.copy_files()

    async def scans(self):
        """扫描目录"""

        async def scan(path):
            self.sync_task.sync_dirs.append(
                await scan_dir(self.client, path)
            )

        for sync_dir in [self.source_dir, *self.target_path]:
            asyncio.create_task(scan(sync_dir), name=f"{id(self)}_scan_{sync_dir}")

        while True:
            await asyncio.sleep(1)
            if not [i.get_name() for i in asyncio.all_tasks() if f"{id(self)}_scan" in i.get_name()]:
                break

        logger.info("扫描完成。")

    def create_copy_task(self, source: SyncDir, target: SyncDir):
        """通过比对源与目标到差异，创建复制列表"""
        for item in source.items:
            item: Item
            copy_path = item.full_name.relative_to(source.base_path)
            name = copy_path.name
            if target.in_items(copy_path):
                # 目标存在，判断是否需要更新
                logger.debug("[%s -> %s] %s: 目标存在", source.base_path, target.base_path, copy_path)
                continue

            task = CopyTask(
                    copy_name=name,  # 需要复制到文件名
                    copy_source=PurePosixPath(source.base_path).joinpath(copy_path.parent),  # 需要复制的源文件夹
                    copy_target=PurePosixPath(target.base_path).joinpath(copy_path.parent),  # 需要复制到的目标文件夹
                )
            self.sync_task.copy_tasks[task.name] = task
            logger.debug("[%s -> %s] %s: 已创建复制任务信息。", source.base_path, target.base_path, copy_path)

    async def create_copy_list(self):
        sync_source = [_s for _s in self.sync_task.sync_dirs if _s.base_path == self.source_dir][0]
        sync_targets = [_s for _s in self.sync_task.sync_dirs if _s.base_path in self.target_path]

        for sync_target in sync_targets:
            sync_target: SyncDir
            self.create_copy_task(sync_source, sync_target)
            logger.info("[%s -> %s] 复制任务信息全部创建完成。", sync_source.base_path, sync_target.base_path)

    async def copy_files(self):
        """复制文件"""

        async def copy(task, *args, **kwargs):
            res = await self.client.copy(*args, **kwargs)
            if res.code == 200:
                task.status = "created"
                self.save_to_cache()
                logger.info("[%s] 复制任务已经在AList中创建。", task.name)
            else:
                logger.warning("[%s] 复制任务创建失败。message: [%d]%s", task.name, res.code, res.message)

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
                        name=f"{id(self)}_copy_{copy_task.copy_name}")
                await asyncio.sleep(5)

        asyncio.create_task(create_copy())
        while True:
            await asyncio.sleep(1)
            task_done = await self.client.task_done('copy')
            await self.client.task_clear_done('copy')
            if await self.client.task_undone('copy'):
                break
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

        logger.info("复制完成。")
