import builtins
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from functools import cached_property, lru_cache
from typing import Optional, Literal, TYPE_CHECKING, Any

from alist_sdk import AlistPathType, AlistPath
from httpx import URL
from pydantic import Field, BaseModel
from pymongo.database import Database

if TYPE_CHECKING:
    from alist_sync.data_handle import ShelveHandle, MongoHandle

logger = logging.getLogger("alist-sync.config")


def create_config():
    """创建配置文件"""
    if hasattr(builtins, "sync_config"):
        return builtins.sync_config

    config_file = os.getenv(
        "ALIST_SYNC_CONFIG", Path(__file__).parent.parent / "config.yaml"
    )

    _sync_config = Config.load_from_yaml(config_file)
    setattr(builtins, "sync_config", _sync_config)
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

    def dump_for_alist_client(self):
        return self.model_dump(exclude={"storage_config"})

    def dump_for_alist_path(self):
        _data = self.model_dump(
            exclude={"storage_config", "max_connect"},
            by_alias=True,
        )
        _data["server"] = _data.pop("base_url")
        return _data

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
    enable: bool = True
    name: str
    type: str
    interval: int = 300
    need_backup: bool = False
    backup_dir: str = ".alist-sync-backup"
    group: list[AlistPathType] = Field(min_length=2)


NotifyType = Literal["email", "webhook"]


class EMailNotify(BaseModel):
    enable: bool = True
    type: NotifyType = "email"
    smtp_host: str
    smtp_port: int = 25
    sender: str
    password: str
    recipients: list[str]


class WebHookNotify(BaseModel):
    enable: bool = True
    type: NotifyType = "webhook"
    webhook_url: str
    headers: dict[str, str]


class Config(BaseModel):
    """配置"""

    def __hash__(self):
        return hash(self._id)

    _id: str = "alist-sync-config"

    cache__dir: Path = Field(
        default=os.getenv(
            "ALIST_SYNC_CACHE_DIR",
            Path(__file__).parent / ".alist-sync-cache",
        ),
        alias="cache_dir",
    )

    timeout: int = Field(10)

    daemon: bool = os.getenv("ALIST_SYNC_DAEMON", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
        "y",
        "t",
        "1",
    )

    runner_name: str = "test"

    mongodb_uri: str | None = os.getenv("ALIST_SYNC_MONGODB_URI", None)

    notify: list[EMailNotify | WebHookNotify] = []

    alist_servers: list[AlistServer] = []
    sync_groups: list[SyncGroup] = []

    create_time: datetime = datetime.now()
    logs: dict = None

    def __init__(self, **data: Any):
        super().__init__(**data)
        import logging.config

        _ = self.start_time
        if self.logs:
            Path("logs").mkdir(exist_ok=True, parents=True)
            logging.config.dictConfig(self.logs)

    @cached_property
    def start_time(self) -> int:
        return int(time.time())

    @cached_property
    def cache_dir(self) -> Path:
        self.cache__dir.mkdir(exist_ok=True, parents=True)
        return self.cache__dir

    @lru_cache(10)
    def get_server(self, base_url) -> AlistServer:
        """找到AlistServer"""
        if isinstance(base_url, AlistPath):
            base_url = base_url.as_uri()
        find_server = URL(base_url)
        for server in self.alist_servers:
            server_ = URL(server.base_url)
            if find_server.host == server_.host and find_server.port == server_.port:
                return server
        raise ModuleNotFoundError()

    @cached_property
    def mongodb(self) -> "Database|None":
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi

        if self.mongodb_uri is None:
            return None

        logger.info("Contenting MongoDB ...")
        db = MongoClient(
            self.mongodb_uri, server_api=ServerApi("1")
        ).get_default_database()
        logger.info(f"Contented MongoDB: {db.client.HOST}/{db.name}")
        if db is None:
            raise ValueError("连接数据库失败")

        return db

    @cached_property
    def handle(self) -> "ShelveHandle|MongoHandle":
        from alist_sync.data_handle import ShelveHandle, MongoHandle

        if self.mongodb is None:
            return ShelveHandle(self.cache_dir)
        return MongoHandle(self.mongodb)

    @classmethod
    def load_from_yaml(cls, file: Path) -> "Config":
        from yaml import safe_load

        return cls.model_validate(safe_load(file.open("rb")))

    def dump_to_yaml(self, file: Path = None):
        from yaml import safe_dump

        return safe_dump(
            self.model_dump(mode="json"),
            file.open("wb") if file else None,
            sort_keys=False,
            allow_unicode=True,
        )

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


sync_config = create_config()


if __name__ == "__main__":
    # config = create_config()
    # print(config)
    # print(config.cache_dir)
    # print(config.mongodb)
    # print(config.notify)
    print(Config.model_json_schema())
