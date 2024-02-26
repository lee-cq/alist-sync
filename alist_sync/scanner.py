# coding: utf8
import asyncio
import logging
from pathlib import PurePosixPath

from alist_sdk import Item, AlistPath
from pydantic import BaseModel

from alist_sync.alist_client import AlistClient
from alist_sync.common import get_alist_client


logger = logging.getLogger("alist-sync.scan-dir")

__all__ = ["scan_dirs", "Scanner"]


class Scanner(BaseModel):
    # scan_path: list[item]
    queue: asyncio.Queue = asyncio.Queue(30)
    items: dict[str | PurePosixPath, list[Item]]

    @classmethod
    async def scans(cls, *scan_path, client: AlistClient = None):
        """扫描目录"""
        client = client or get_alist_client()
        return cls(
            items={
                k: v
                for k, v in await asyncio.gather(
                    *[cls.scan(path, client) for path in scan_path]
                )
            }
        )

    @classmethod
    async def retry(cls, client, _path, _rt=5) -> list[Item]:
        __res = await client.list_files(_path, refresh=True)
        if __res.code != 200:
            logger.warning(f"扫描目录异常: {_path=} {__res.code=} {__res.message=}")
            if _rt:
                return await cls.retry(client, _path, _rt=_rt - 1)
            exit(1)
        return __res.data.content or []

    @classmethod
    async def get_files(cls, client, _path, output):
        _path = PurePosixPath(_path)
        if _path.name == ".alist-sync-data":
            logger.debug("跳过 .alist-sync-data ...")
            return

        __res = await cls.retry(client, _path)
        for _item in __res:
            _item: Item
            _item.parent = _path
            if _item.is_dir:
                # noinspection PyAsyncCall
                asyncio.create_task(
                    cls.get_files(client, _item.full_name, output),
                    name=f"scan_{_item.full_name}",
                )
            else:
                # _list.append(_item)
                await cls.queue.put(_item)
                logger.debug("find: %s", _item.full_name)
                return _item

    @classmethod
    async def scan(
        cls,
        path: str | PurePosixPath,
        client: AlistClient,
        output: list | asyncio.Queue = None,
    ) -> tuple[str, list[Item]]:
        """扫描目录"""
        if output is None:
            output: list[Item] = []

        logger.info("扫描目录 %s 中的文件.", path)
        await cls.get_files(client, path, output)
        await cls.lock()
        return path, output

    @staticmethod
    async def lock():
        pre = f"scan"
        while True:
            await asyncio.sleep(1)
            names = [i.get_name() for i in asyncio.all_tasks() if pre in i.get_name()]
            logger.debug("lock: %s: %s", pre, names)
            if not names:
                return


async def scan_dirs(*scan_path, client: AlistClient = None) -> Scanner:
    """扫描目录"""
    client = client or get_alist_client()
    return await Scanner.scans(*scan_path, client=client)
