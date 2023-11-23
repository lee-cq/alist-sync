# coding: utf8
import asyncio
import logging

from alist_sdk import AsyncClient, Item, RequestError
from .models import SyncDir, AlistServer

logger = logging.getLogger("alist-sync.scan-dir")

__all__ = ["scan_dir"]


class ScanDir:
    def __init__(self, client: AsyncClient):
        self.client = client
        self.itme_list: list[Item] = []

    async def lock(self):
        pre = f"{id(self)}_scan"
        while True:
            await asyncio.sleep(1)
            if not [i.get_name() for i in asyncio.all_tasks() if pre in i.get_name()]:
                return

    async def scan(self, path):
        logger.info('扫描目录 %s 中的文件.', path)
        res = await self.client.list_files(path, per_page=0, refresh=True)
        if res.code != 200:
            raise RequestError(f"[code: {res.code}] {res.message}")
        for item in res.data.content or []:
            item: Item
            item.parent = path
            if item.is_dir:
                asyncio.create_task(self.scan(item.full_name), name=f"{id(self)}_scan_{path}")
            else:
                self.itme_list.append(item)


async def scan_dir(alist_info: AlistServer, scan_path) -> SyncDir:
    """扫描目录"""
    _ac = AsyncClient(base_url=alist_info.base_url, verify=False, timeout=30)
    if alist_info.token:
        await _ac.set_token(alist_info.token)
    if alist_info.username:
        logger.info("使用username登陆: %s", alist_info.username)
        await _ac.login(alist_info.username, alist_info.password)

    _s = ScanDir(_ac)
    await _s.scan(scan_path)
    await _s.lock()
    return SyncDir(base_path=scan_path, items=_s.itme_list)
