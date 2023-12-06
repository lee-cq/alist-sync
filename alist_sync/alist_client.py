import asyncio
import logging
import time

from alist_sdk import AsyncClient as _AsyncClient, Task

from .common import async_all_task_names

logger = logging.getLogger("alist-sync.client")

__all__ = ["AlistClient"]


class TaskStat:
    copy_task_done = 0, []
    copy_task_undone = 0, []


class AlistClient(_AsyncClient):

    def __init__(self, base_url, max_connect=30, *,
                 token=None, username=None, password=None, has_opt=False, **kwargs):
        super().__init__(base_url, token, username=username, password=password, has_opt=has_opt, **kwargs)
        self._max_connect = asyncio.Semaphore(max_connect)

    def set_mex_connect(self, max_connect):
        """"""
        self._max_connect = asyncio.Semaphore(max_connect)

    async def request(self, *args, **kwargs):
        async with self._max_connect:
            return await super().request(*args, **kwargs)

    async def _cache(self, attr_name, task_type):
        wait_time = 0.01
        while True:
            await asyncio.sleep(wait_time)
            if self.is_closed:
                break
            res = await self.__getattribute__(attr_name)(task_type)
            if res.code == 200:
                setattr(
                    TaskStat, f"{task_type}_{attr_name}",
                    (
                        int(time.time()),
                        res.data or []
                    )
                )
                wait_time = 5
            else:
                wait_time = 0.1

    @property
    def cached_copy_task_done(self) -> tuple[int, list[Task]]:
        """

        :return 更新时间, {task_name, Task, ...}
        """
        if "cached_copy_task_done" not in async_all_task_names():
            asyncio.create_task(
                self._cache('task_done', 'copy'),
                name='cached_copy_task_done'
            )
        return TaskStat.copy_task_done

    @property
    def cached_copy_task_undone(self) -> tuple[int, list[Task]]:
        """

        :return 更新时间, {task_name, Task, ...}
        """
        if "cached_copy_task_done" not in async_all_task_names():
            asyncio.create_task(
                self._cache('task_undone', 'copy'),
                name='cached_copy_task_done'
            )
        return TaskStat.copy_task_undone
