import builtins
import json
import os
from datetime import datetime
from pathlib import Path
from functools import cached_property
from typing import Optional

from alist_sdk import AlistPathType
from pydantic import Field, BaseModel
from pymongo.database import Database


def create_config():
    """创建配置文件"""
    if hasattr(builtins, "sync_config"):
        return builtins.sync_config

    config_file = os.getenv(
        "ALIST_SYNC_CONFIG", Path(__file__).parent.parent / "config.yaml"
    )

    sync_config = Config.load_from_yaml(config_file)
    setattr(builtins, "sync_config", sync_config)
    return sync_config


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

    def dump_for_sdk(self):
        return self.model_dump(exclude={"storage_config"})

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


class SyncGroup(BaseModel):
    name: str
    type: str
    group: list[AlistPathType] = Field(min_length=2)


class Config(BaseModel):
    """配置"""

    _id: str = "alist-sync-config"

    cache__dir: Path = Field(
        default=os.getenv("ALIST_SYNC_CACHE_DIR") or Path(__file__).parent / ".cache",
        alias="cache_dir",
    )

    daemon: bool = os.getenv("ALIST_SYNC_DAEMON", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
        "y",
        "t",
        "1",
    )

    mongodb_uri: str | None = os.getenv("ALIST_SYNC_MONGODB_URI", None)

    alist_servers: list[AlistServer] = []
    sync_groups: list[SyncGroup] = []

    create_time: datetime = datetime.now()

    @cached_property
    def cache_dir(self) -> Path:
        self.cache__dir.mkdir(exist_ok=True, parents=True)
        return self.cache__dir

    @cached_property
    def mongodb(self) -> "Database":
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi

        db = MongoClient(
            self.mongodb_uri, server_api=ServerApi("1")
        ).get_default_database()
        if db is None:
            raise ValueError("连接数据库失败")

        return db

    @classmethod
    def load_from_yaml(cls, file: Path) -> "Config":
        from yaml import safe_load

        return cls.model_validate(safe_load(file.open("rb")))

    def dump_to_yaml(self, file: Path):
        from yaml import safe_dump

        return safe_dump(self.model_dump(mode="json"), file.open("wb"))

    def load_from_mongo(self, uri: str = None):
        from pymongo import MongoClient

        col = MongoClient(uri).get_default_database()["config"]
        data = col.find_one({"_id": self._id})
        return self.model_validate(data)

    def dump_to_mongodb(self):
        return self.mongodb["config"].update_one(
            {"_id": self._id},
            {"$set": self.model_dump(mode="json")},
            True,
        )


if __name__ == "__main__":
    config = create_config()
    print(config)
    print(config.cache_dir)
    print(config.mongodb)
