import datetime
import json
from pathlib import PurePosixPath, Path
from typing import Optional, Literal

from pydantic import BaseModel, computed_field, Field
from alist_sdk import Item

from alist_sync.alist_client import AlistClient

__all__ = ["AlistServer", "SyncDir", "RemoveTask", "SyncJob", ]


class AlistServer(BaseModel):
    """"""
    base_url: str = 'http://localhost:5244'
    username: Optional[str] = ''
    password: Optional[str] = ''
    token: Optional[str] = None
    has_opt: Optional[bool] = False

    max_connect: int = 30  # 最大同时连接数
    storage_config: Optional[Path] = None

    # httpx 的参数
    verify: Optional[bool] = True
    headers: Optional[dict] = None

    def storages(self) -> list[dict]:
        """返回给定的 storage_config 中包含的storages"""

        def is_storage(_st):
            if not isinstance(_st, dict):
                return False
            if 'mount_path' in _st and 'driver' in _st:
                return True
            return False

        if not self.storage_config or self.storage_config == Path():
            return []
        if not self.storage_config.exists():
            raise FileNotFoundError(f"找不到文件：{self.storage_config}")

        _load_storages = json.load(self.storage_config.open())
        if isinstance(_load_storages, list):
            _load_storages = [_s for _s in _load_storages if is_storage(_s)]
            if _load_storages:
                return _load_storages
            raise KeyError()

        if isinstance(_load_storages, dict):
            if 'storages' in _load_storages:
                _load_storages = [
                    _s for _s in _load_storages['storages'] if is_storage(_s)
                ]
                if _load_storages:
                    return _load_storages
                raise KeyError()
            if is_storage(_load_storages):
                return [_load_storages, ]
            raise KeyError("给定的")


class SyncDir(BaseModel):
    """同步目录模型，定义一个同步目录"""
    base_path: str  # 同步基础目录
    items: list[Item]  # Item列表

    items_relative: Optional[list] = Field([], exclude=True)  # Item列表相对路径

    def in_items(self, path) -> bool:
        """判断path是否在items中"""
        if not self.items_relative:
            self.items_relative = [i.full_name.relative_to(
                self.base_path) for i in self.items]
        return path in self.items_relative


class RemoveTask(BaseModel):
    """删除文件的任务"""
    full_path: PurePosixPath | str
    status: str = 'init'


class SyncJob(BaseModel):
    """同步任务"""
    alist_info: AlistServer  # Alist Info
    sync_dirs: dict[str, SyncDir] = {}  # 同步目录
    checker: Optional['Checker'] = None


class Config(BaseModel):
    """配置"""
    name: str
    alist_info: AlistServer
    config_dir: PurePosixPath
    cache_dir: Path
    sync_group: list[str]

    update_time: datetime.datetime
    create_time: datetime.datetime
