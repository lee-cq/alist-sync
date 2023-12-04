import logging
import asyncio

from .alist_client import AlistClient
from .config import cache_dir
from .models import SyncTask, AlistServer
from .scan_dir import scan_dir
from .common import sha1_6

logger = logging.getLogger("alist-sync.base")


class SyncBase:

    def __init__(self,
                 alist_info: AlistServer,
                 mode: str = 'copy',
                 source_dir: str = None,
                 target_path: list[str] = []
                 ):
        self.mode = mode
        self.client = AlistClient(timeout=30, **alist_info.model_dump())
        self.target_path = target_path
        self.source_dir = source_dir
        target_path.sort()
        self.sync_task_cache_file = cache_dir.joinpath(
            f"sync_task_{sha1_6(source_dir)}_{sha1_6(target_path)}.json"
        )
        logger.info("缓存文件名: %s -> %s : %s .",
                    source_dir,
                    target_path,
                    self.sync_task_cache_file
                    )
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
        self.sync_task = SyncTask.model_validate_json(
            self.sync_task_cache_file.read_text())

    def save_to_cache(self):
        """保存到缓存中"""
        self.sync_task_cache_file.write_text(
            self.sync_task.model_dump_json(indent=2)
        )

    async def scans(self):
        """扫描目录"""

        async def scan(path):
            self.sync_task.sync_dirs.append(
                await scan_dir(self.client, path)
            )

        for sync_dir in [self.source_dir, *self.target_path]:
            asyncio.create_task(
                scan(sync_dir), name=f"{id(self)}_scan_{sync_dir}")

        while True:
            await asyncio.sleep(1)
            if not [i.get_name() for i in asyncio.all_tasks() if f"{id(self)}_scan" in i.get_name()]:
                break

        logger.info("扫描完成。")

    def run(self):
        asyncio.run(self.async_run())

    async def async_run(self):
        if not self.sync_task.sync_dirs.syncs:
            await self.scans()
            self.save_to_cache()
        else:
            logger.info(f"一件从缓存中找到 %d 个 SyncDir",
                        len(self.sync_task.sync_dirs.syncs))
