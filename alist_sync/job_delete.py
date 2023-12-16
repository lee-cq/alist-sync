from pathlib import PurePosixPath
from pydantic import BaseModel


class DeleteTask(BaseModel):
    """删除文件的任务"""
    full_path: PurePosixPath | str
    status: str = 'init'


class DeleteJob(BaseModel):
    """"""
