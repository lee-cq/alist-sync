import builtins
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from functools import cached_property, lru_cache
from typing import Optional, Literal, TYPE_CHECKING, Any, Annotated

from alist_sdk import AlistPathType, AlistPath
from alist_sdk.path_lib import AlistPathPydanticAnnotation
from httpx import URL
from pydantic import Field, BaseModel, BeforeValidator
from pymongo.database import Database

from alist_sync.common import data_size_to_bytes


if TYPE_CHECKING:
    from alist_sync.data_handle import ShelveHandle, MongoHandle

logger = logging.getLogger("alist-sync.config")

PAlistPathType = Annotated[
    AlistPathType,
    AlistPathPydanticAnnotation,
    BeforeValidator(
        lambda x: (
            URL("http://localhost:5244").join(x).__str__()
            if not URL(x).is_absolute_url
            else x
        )
    ),
]

TrueValues = {"true", "1", "yes", "on", "y", "t"}
FalseValues = {"false", "0", "no", "off", "n", "f"}

B = 1
KB = B * 1024
MB = KB * 1024
GB = MB * 1024


def getenv(name, default=None):
    """获取环境变量"""
    return os.getenv(name, os.getenv("_" + name, default))


def create_config():
    """创建配置文件"""
    if hasattr(builtins, "sync_config"):
        return builtins.sync_config

    config_file = getenv(
        "ALIST_SYNC_CONFIG", Path(__file__).parent.parent / "config.yaml"
    )

    _sync_config = Config.load_from_yaml(config_file)
    setattr(builtins, "sync_config", _sync_config)
    return _sync_config


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


def set_add(x) -> set:
    x = set(x)
    x.add(".alist-sync*")
    return x


class SyncGroup(BaseModel):
    def __hash__(self):
        return hash(self.name + self.type)

    enable: bool = True
    name: str
    type: str
    interval: int = 300
    need_backup: bool = False
    backup_dir: str = ".alist-sync-backup"
    blacklist: Annotated[set[str], BeforeValidator(lambda x: x + [".alist-sync*"])] = {}
    whitelist: Annotated[set[str], BeforeValidator(lambda x: x)] = {}
    group: list[PAlistPathType] = Field(min_length=2)


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

    _id: str = getenv("ALIST_SYNC_NAME", "alist-sync")

    _cache_dir: Path = Field(
        default=getenv(
            "ALIST_SYNC_CACHE_DIR",
            Path(__file__).parent / ".alist-sync-cache",
        ),
        alias="cache_dir",
    )
    _cache_max_size: Annotated[int, BeforeValidator(data_size_to_bytes)] = Field(
        getenv("ALIST_SYNC_CACHE_MAX_SIZE", "0"),
        alias="cache_max_size",
    )

    timeout: int = Field(10)
    ua: str = None

    daemon: bool = getenv("ALIST_SYNC_DAEMON", "false").lower() in TrueValues

    name: str = getenv("ALIST_SYNC_NAME", "alist-sync")

    mongodb_uri: str | None = getenv("ALIST_SYNC_MONGODB_URI", None)

    notify: list[EMailNotify | WebHookNotify] = []

    alist_servers: list[AlistServer] = []
    sync_groups: list[SyncGroup] = []

    create_time: datetime = datetime.now()
    logs: dict = None

    debug: bool = getenv("ALIST_SYNC_DEBUG", "false").lower() in TrueValues

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
        self._cache_dir.mkdir(exist_ok=True, parents=True)
        return self._cache_dir

    @cached_property
    def cache_max_size(self) -> int:
        if self._cache_max_size > 0:
            return int(self._cache_max_size)

        import psutil

        if self._cache_max_size == 0:
            return psutil.disk_usage(self.cache_dir.__str__()).free // 2
        else:
            return psutil.disk_usage(self.cache_dir.__str__()).free

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


if __name__ == "__main__":
    print(Config.model_json_schema())
