import datetime
import json
from pathlib import PurePosixPath, Path
from typing import Optional

from pydantic import BaseModel as _BaseModel

__all__ = [
    "BaseModel",
    "AlistServer",
]

from alist_sync.config import cache_dir


class BaseModel(_BaseModel):
    """基础模型"""

    @classmethod
    def from_json_file(cls, file: Path):
        """从文件中读取json"""
        if not file.exists():
            raise FileNotFoundError(f"找不到文件：{file}")
        return cls.model_validate_json(Path(file).read_text(encoding="utf-8"))

    @classmethod
    def from_cache(cls):
        class_name = cls.__name__
        file = cache_dir.joinpath(f"{class_name}.json")
        return cls.from_json_file(file)

    def save_to_cache(self):
        class_name = self.__class__.__name__
        file = cache_dir.joinpath(f"{class_name}.json")
        file.write_text(self.model_dump_json(indent=2), encoding="utf-8")


class AlistServer(BaseModel):
    """"""

    base_url: str = "http://localhost:5244"
    username: Optional[str] = ""
    password: Optional[str] = ""
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
            if "mount_path" in _st and "driver" in _st:
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
            if "storages" in _load_storages:
                _load_storages = [
                    _s for _s in _load_storages["storages"] if is_storage(_s)
                ]
                if _load_storages:
                    return _load_storages
                raise KeyError()
            if is_storage(_load_storages):
                return [
                    _load_storages,
                ]
            raise KeyError("给定的")


class Config(BaseModel):
    """配置"""

    name: str
    alist_info: AlistServer
    config_dir: PurePosixPath
    cache_dir: Path
    sync_group: list[str]

    update_time: datetime.datetime
    create_time: datetime.datetime
