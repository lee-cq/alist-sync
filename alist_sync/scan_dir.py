# coding: utf8
import asyncio
import logging
from pathlib import PurePosixPath

from alist_sdk import Item
from .models import SyncDir

from .alist_client import AlistClient

logger = logging.getLogger("alist-sync.scan-dir")

__all__ = ["scan_dir"]


class ScanDir:
    def __init__(self, client: AlistClient):
        self.client = client
        self.itme_list: list[Item] = []

    async def async_run(self, scan_path):
        """异步运行"""
        await self.scan(scan_path)
        await self.lock()
        return SyncDir(base_path=scan_path, items=self.itme_list)

    async def lock(self):
        pre = f"{id(self)}_scan"
        while True:
            await asyncio.sleep(1)
            if not [i.get_name() for i in asyncio.all_tasks() if pre in i.get_name()]:
                return

    async def list_files(self, path, retry=5):
        """列出目录"""
        res = await self.client.list_files(path, refresh=True)
        if res.code != 200:
            logger.warning("扫描目录异常：[code: %d] %s", res.code, res.message)
            if retry:
                return await self.list_files(path=path, retry=retry - 1)
            exit(1)
        return res

    async def scan(self, path):
        logger.info('扫描目录 %s 中的文件.', path)
        if isinstance(path, PurePosixPath):
            path = path.as_posix()
        res = await self.list_files(path=path)
        for item in res.data.content or []:
            item: Item
            item.parent = path
            if item.is_dir:
                asyncio.create_task(
                    self.scan(item.full_name),
                    name=f"{id(self)}_scan_{path}"
                )
            else:
                self.itme_list.append(item)


async def scan_dir(client: AlistClient, scan_path) -> SyncDir:
    """扫描目录"""
    return await ScanDir(client).async_run(scan_path)
