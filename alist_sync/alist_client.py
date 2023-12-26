import asyncio
import builtins
import logging
import time
from typing import Literal

from alist_sdk import AsyncClient as _AsyncClient, Task
from async_lru import alru_cache as lru_cache

from alist_sync.common import get_alist_client

logger = logging.getLogger("alist-sync.client")

__all__ = ["AlistClient", "get_status"]

CopyStatusModify = Literal[
    "init",
    "created",
    "waiting",
    "getting src object",
    "",
    "running",
    "success",
    "failed",
    "checked_done",
]


class AlistClient(_AsyncClient):
    def __init__(
        self,
        base_url,
        max_connect=30,
        *,
        token=None,
        username=None,
        password=None,
        has_opt=False,
        **kwargs,
    ):
        super().__init__(
            base_url,
            token,
            username=username,
            password=password,
            has_opt=has_opt,
            **kwargs,
        )

        self._max_connect = asyncio.Semaphore(max_connect)
        self.__closed = False
        setattr(builtins, "alist_client", self)

    def close(self):
        self.__closed = True

    def set_mex_connect(self, max_connect):
        """"""
        self._max_connect = asyncio.Semaphore(max_connect)

    async def request(self, *args, **kwargs):
        async with self._max_connect:
            return await super().request(*args, **kwargs)

    @staticmethod
    def __task_rtype(rtype, data):
        if rtype == list:
            return data or []
        return {i.name: i for i in data or []}

    @lru_cache(maxsize=1)
    async def cached_task_done(
        self, task_type, rtype: object = list, timestamp=0
    ) -> tuple[int, list[Task] | dict[str, Task]]:
        """获取已完成的任务"""
        res = await self.task_done(task_type)
        if res.code == 200:
            return timestamp * 5, self.__task_rtype(rtype, res.data)
        raise ValueError(f"获取已完成的任务失败: {res.code = } {res.message = }")

    @lru_cache(maxsize=1)
    async def cached_task_undone(
        self, task_type, rtype: object = list, timestamp=0
    ) -> tuple[int, list[Task] | dict[str, Task]]:
        """获取未完成的任务"""
        res = await self.task_undone(task_type)
        if res.code == 200:
            return timestamp * 5, self.__task_rtype(rtype, res.data)
        raise ValueError(f"获取未完成的任务失败: {res.code = } {res.message = }")


async def get_status(
    task_name, client: AlistClient = None
) -> tuple[CopyStatusModify, int | float]:
    """获取任务状态

    :param client: AlistClient
    :param task_name: 任务名称
    :return: 任务状态(状态名称，状态进展)
    """
    client = client or get_alist_client()
    (_, _task_done), (_, _task_undone) = await asyncio.gather(
        client.cached_task_done("copy", dict, int(time.time()) // 5),
        client.cached_task_undone("copy", dict, int(time.time()) // 5),
    )
    if task_name in _task_done and task_name not in _task_undone:
        return "success", 100
    elif task_name in _task_undone:
        return _task_undone[task_name].status, _task_undone[task_name].progress
    else:
        raise ValueError(f"任务不存在: {task_name}")


if __name__ == "__main__":
    _c = AlistClient(
        base_url="http://localhost:5244",
        username="admin",
        password="123456",
        verify=False,
    )
    asyncio.run(_c.me())
