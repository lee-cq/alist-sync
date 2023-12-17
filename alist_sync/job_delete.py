from pathlib import PurePosixPath
from pydantic import BaseModel

from alist_sync.checker import Checker


class DeleteTask(BaseModel):
    """删除文件的任务"""

    full_path: PurePosixPath | str
    status: str = "init"


class DeleteJob(BaseModel):
    """"""

    tasks = dict[PurePosixPath | str, DeleteTask]
    done_tasks = dict[PurePosixPath | str, DeleteTask]

    @classmethod
    def from_checker(cls, checker: Checker):
        """"""
        tasks = {}
        for i in checker.delete:
            tasks[i.full_path] = DeleteTask(full_path=i.full_path)
        return cls(tasks=tasks)
