#!/bin/env python3
# coding: utf8
import logging
import os
from pathlib import Path

from typer import Typer, Option, echo


app = Typer()


_stores_config: str | None = Option(
    None, "-c", "--store-path", help="一个包含存储配置的JSON文件，可以是AList的备份文件"
)


@app.command("test-config")
def t_config(config_file: str = Option(None, "--config", "-c", help="配置文件路径")):
    """测试配置"""
    from alist_sync.config import create_config

    if config_file and Path(config_file).exists():
        os.environ["ALIST_SYNC_CONFIG"] = str(Path(config_file).resolve().absolute())

    _c = create_config()
    echo(_c.dump_to_yaml())
    logger.info("Done.")


@app.command("sync")
def sync(config_file: str = Option(None, "--config", "-c", help="配置文件路径")):
    """同步任务"""
    from alist_sync.config import create_config
    from alist_sync.d_main import main

    if config_file and Path(config_file).exists():
        os.environ["ALIST_SYNC_CONFIG"] = str(Path(config_file).resolve().absolute())

    create_config()
    return main()


@app.command("get-info")
def cli_get(path: str):
    """"""
    from alist_sdk import login_server, AlistPath
    from alist_sync.config import sync_config

    for s in sync_config.alist_servers:
        login_server(**s.dump_for_alist_path())

    echo(AlistPath(path).re_stat(retry=5, timeout=3).model_dump_json(indent=2))


if __name__ == "__main__":
    from rich.logging import RichHandler

    logger = logging.getLogger("alist-sync")
    handler = RichHandler()
    handler.setLevel("DEBUG")
    logger.addHandler(handler)
    logger.setLevel("DEBUG")
    app()
