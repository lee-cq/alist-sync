#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : config.py.py
@Author     : LeeCQ
@Date-Time  : 2024/8/19 0:27
"""
import logging
import os
from pathlib import Path
from typing import Optional
from functools import cached_property
from yaml import safe_load

import peewee
from playhouse.db_url import connect as connect_db
from pydantic import BaseModel
from alist_sdk import AlistPath, AlistPathType, login_server

__all__ = ["load_env", "Database", "Config", "config"]

from alist_sync.common import sha1
from alist_sync.const import Env

logger = logging.getLogger("alist-sync.config")


def load_env():
    def __load_env(file: Path):
        print("Load Env From:", file)
        for line in file.read_text().split("\n"):
            line = line.strip().strip("\t")
            if line == "" or line.startswith("#") or line.startswith(";"):
                continue
            k, v = line.split("=", 1)
            os.environ[k] = v
            print(f"[Info] Load Env: {k=} {v=}")

    _code = Path(__file__).parent
    if _code.joinpath(".env").exists():
        __load_env(_code.joinpath(".env"))

    _code_root = _code.parent
    if _code_root.joinpath(".env").exists():
        __load_env(_code_root.joinpath(".env"))

    if Path().joinpath(".env").exists():
        __load_env(Path().joinpath(".env"))


class Database(BaseModel):
    type: Optional[str] = "sqlite"  # mysql or SQLite or Postgresql[pg]
    url: Optional[str] = ""
    path: Optional[str] = ".data.db"  # SQLite 默认数据库存储位置
    host: Optional[str] = "localhost"
    port: Optional[int] = 3306
    username: Optional[str] = "test"
    password: Optional[str] = "test"
    database: Optional[str] = "alist-sync"

    @cached_property
    def db(self) -> peewee.Database:
        if self.url:
            return connect_db(self.url)

        _dbc = {
            "sqlite": peewee.SqliteDatabase,
            "mysql": peewee.MySQLDatabase,
            "postpresql": peewee.PostgresqlDatabase,
            "": peewee.Database,
        }.get(self.type)

        if self.type.lower() == "sqlite":
            return _dbc(self.path)
        elif self.type.lower() in ["mysql", "postgresql", "pg"]:
            return _dbc(
                self.database,
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
            )


class AlistServer(BaseModel):
    base_url: str = "http://localhost:8080"
    username: str = "admin"
    password: str = "admin"
    verity: bool = True
    timeout: int = 10

    def login(self):
        login_server(
            self.base_url,
            username=self.username,
            password=self.password,
            verify=self.verity,
            timeout=self.timeout,
        )


class SyncGroup(BaseModel):
    enabled: bool = True
    name: str
    max_workers: int = 5  # 最大同步线程数
    sync_type: str = "copy"  # copy or mirror
    sync_path: list[AlistPathType]
    need_backup: bool = True
    # backup_path: str = ".alist-sync-backup"
    exclude: list[str] = []
    include: list[str] = []

    def get_backup_path(self, target_path: AlistPath | None) -> None | AlistPath:
        """"""

        def _get_base_dir(_t: AlistPath) -> AlistPath:
            for sp in self.sync_path:
                try:
                    _t.relative_to(sp)
                    return sp
                except ValueError:
                    pass

        if target_path is None or not target_path.exists() or not self.need_backup:
            return None

        name = f"{sha1(target_path.as_posix())}_{int(target_path.stat().modified.timestamp())}.history"
        return _get_base_dir(target_path).joinpath(".alist-sync-backup", name)


class Config(BaseModel):
    version: str = "1"  #
    database: Database = Database()  # 数据库存储，默认SQLite
    alist_servers: list[AlistServer]  # Alist 服务器配置信息
    sync_groups: list[SyncGroup]  # 同步组配置信息
    logs: dict

    @classmethod
    def load_from_yaml(cls, file: str) -> "Config":
        dc = safe_load(Path(file).read_text())
        return cls.model_validate(dc)

    def login(self):
        for server in self.alist_servers:
            server.login()

    def loda_logger(self):
        if self.logs:
            from logging import config

            config.dictConfig(self.logs)


load_env()
config = Config.load_from_yaml(os.getenv(Env.config, "config.yaml"))
config.login()
config.loda_logger()
logger.info("COnfig Load Success.")
