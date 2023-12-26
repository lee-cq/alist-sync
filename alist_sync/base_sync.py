import asyncio
import logging
import os

from alist_sdk import Client

from alist_sync.alist_client import AlistClient
from alist_sync.common import timeout_input
from alist_sync.models import AlistServer

logger = logging.getLogger("alist-sync.base")


class SyncBase:
    def __init__(self, alist_info: AlistServer, sync_dirs: list[str | os.PathLike]):
        self.client = AlistClient(timeout=30, **alist_info.dump_for_sdk())
        self._client = Client(timeout=30, **alist_info.dump_for_sdk())

        self.sync_dirs = sync_dirs
        self.sync_dirs.sort()
        self.alist_info = alist_info

    async def create_storages(self, storages):
        """创建后端存储"""
        mounted_storages = [
            s.mount_path for s in (await self.client.admin_storage_list()).data.content
        ]
        for st in storages:
            if st["mount_path"] in mounted_storages:
                logger.error("Mount_Path重复，可能会造成错误：%s", st["mount_path"])
                if timeout_input("3s内觉得是否继续 (y/N):", default="N").upper() != "Y":
                    raise
                continue
            res = await self.client.admin_storage_create(st)
            if res.code == 200:
                logger.info("创建存储成功: %s, id=%s", st["mount_path"], res.data.id)
            else:
                raise Exception(
                    f"创建存储失败：%s, message: %s", st["mount_path"], res.message
                )

    async def verify_sync_dir(self):
        """验证同步的目录是存在的，因为增量同步有可能会在scanner之前操作数据。"""
        for s_dir in self.sync_dirs:
            res = await self.client.get_item_info(s_dir)
            if res.code == 404:
                raise FileNotFoundError(f"{s_dir} 不存在于 Alist 中。")

    def run(self):
        asyncio.run(self.async_run())

    async def async_run(self):
        await self.create_storages(self.alist_info.storages())
        await self.verify_sync_dir()
