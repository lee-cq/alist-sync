import logging
from pathlib import PurePosixPath
from typing import Iterator, Literal

from pydantic import BaseModel

from alist_sync.alist_client import AlistClient
from alist_sync.checker import Checker
from alist_sync.common import get_alist_client
from alist_sync.jobs import JobBase

logger = logging.getLogger("alist-sync.job_remove")
CopyStatusModify = Literal[
    "init",
    "removed",
    "checked_done",
]


class RemoveTask(BaseModel):
    """删除文件的任务"""

    full_path: PurePosixPath | str
    status: str = "init"
    error_times: int = 0

    @property
    def name(self) -> str | PurePosixPath:
        return self.full_path

    async def remove(self, client: AlistClient = None):
        """删除文件"""
        client = client or get_alist_client()
        res = await client.remove(self.full_path.parent, self.full_path.name)
        if res.code == 200:
            logger.info("删除文件 %s 成功", self.full_path)
            self.status = "removed"
            return True
        logger.error(f"删除文件 {self.full_path} 失败: [{res.code=}]{res.message}")
        self.error_times += 1
        return False

    async def recheck(self, client: AlistClient = None) -> bool:
        """重新检查"""
        client: AlistClient = client or get_alist_client()
        res = await client.get_item_info(self.name)
        if res == 404:
            self.status = "rechecked_done"
            return True
        self.error_times += 1
        return False

    async def check_status(self, client: AlistClient = None) -> bool:
        """检查任务状态"""
        client = client or get_alist_client()
        if self.status == "init":
            return await self.remove(client)
        elif self.status == "removed":
            return await self.recheck(client)
        elif self.status == "checked_done":
            return True
        else:
            raise ValueError(f"未知的状态：{self.status}")


class RemoveJob(JobBase):
    """"""

    tasks: dict[PurePosixPath | str, RemoveTask]
    done_tasks: dict[PurePosixPath | str, RemoveTask] = {}

    @staticmethod
    def create_task(_s, _t, checker: Checker) -> Iterator[RemoveTask]:
        """创建任务
        _s 无 _t 有：删除 _t
        """
        _s, _t = PurePosixPath(_s), PurePosixPath(_t)
        if _s not in checker.cols and _t not in checker.cols:
            raise ValueError(f"Source: {_s} or Target: {_t} not in Checker")

        for r_path, pp in checker.matrix.items():
            if pp.get(_s) is None and pp.get(_t) is not None:
                yield RemoveTask(full_path=pp.get(_t).full_name)
