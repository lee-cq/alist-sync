import os
import logging
import asyncio

from .alist_client import AlistClient
from .config import cache_dir
from .models import SyncTask, AlistServer
from .scan_dir import scan_dir
from .common import sha1_6, is_task_all_success, timeout_input

logger = logging.getLogger("alist-sync.base")


class SyncBase:

    def __init__(self,
                 alist_info: AlistServer,
                 sync_dirs: list[str | os.PathLike]
                 ):
        self.client = AlistClient(
            timeout=30, **alist_info.model_dump(exclude='storage_config')
        )

        self.sync_dirs = sync_dirs
        self.sync_dirs.sort()

        self.sync_task_cache_file = cache_dir.joinpath(
            f"sync_task_{sha1_6(self.sync_dirs)}.json"
        )
        self.sync_task = SyncTask(
            alist_info=alist_info,
        )
        self.load_from_cache()

    def __del__(self):
        self.client.close()
        self.save_to_cache()
        self.clear_cache()

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

    def clear_cache(self, force=False):
        """清除缓存"""
        if force:
            self.sync_task_cache_file.unlink(missing_ok=True)
        if all((is_task_all_success(self.sync_task.copy_tasks),
                is_task_all_success(self.sync_task.remove_tasks)
                )):
            self.sync_task_cache_file.unlink(missing_ok=True)

    async def create_storages(self, storages):
        """创建后端存储"""
        mounted_storages = [s.mount_path for s in (await self.client.storage_list()).data.content]
        for st in storages:
            if st['mount_path'] in mounted_storages:
                logger.error("Mount_Path重复，可能会造成错误：%s", st['mount_path'])
                if timeout_input("3s内觉得是否继续 (y/N):", default='N').upper() != "Y":
                    raise
                continue
            res = await self.client.storage_create(st)
            if res.code == 200:
                logger.info("创建存储成功: %s, id=%s", st['mount_path'], res.data.id)
            else:
                raise Exception(f"创建存储失败：%s, message: %s",
                                st['mount_path'], res.message)

    async def scans(self):
        """扫描目录"""

        async def scan(path):
            self.sync_task.sync_dirs.setdefault(
                path, await scan_dir(self.client, path)
            )

        for sync_dir in self.sync_dirs:
            asyncio.create_task(
                scan(sync_dir), name=f"{id(self)}_scan_{sync_dir}"
            )

        while True:
            await asyncio.sleep(1)
            if not [i.get_name() for i in asyncio.all_tasks() if f"{id(self)}_scan" in i.get_name()]:
                break

        logger.info("扫描完成。")

    def run(self):
        asyncio.run(self.async_run())

    async def async_run(self):
        await self.create_storages(self.sync_task.alist_info.storages())
        if not self.sync_task.sync_dirs.values():
            await self.scans()
            self.save_to_cache()
        else:
            logger.info(f"一件从缓存中找到 %d 个 SyncDir",
                        len(self.sync_task.sync_dirs))
