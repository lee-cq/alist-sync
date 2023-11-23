from typing import Optional

from pydantic import BaseModel
from alist_sdk import Item

__all__ = ["AlistServer", "SyncDir", "CopyTask", "SyncTask"]


class AlistServer(BaseModel):
    """"""
    base_url: str
    username: Optional[str] = ''
    password: Optional[str] = ''
    token: Optional[str] = None
    has_opt: Optional[bool] = False

    # httpx 的参数
    verify: Optional[bool] = True


class SyncDir(BaseModel):
    """同步目录模型，定义一个同步目录"""
    base_path: str  # 同步基础目录
    items: list[Item]  # Item列表


class CopyTask(BaseModel):
    """复制任务"""
    copy_id: str
    copy_name: str
    source_path: str
    target_name: str
    status: str


class SyncTask(BaseModel):
    """同步任务"""
    alist_info: AlistServer  # Alist Info
    sync_dirs: list[SyncDir]  # 同步目录
    copy_tasks: list[CopyTask]  # 复制目录
