#!/bin/env python3
import logging.config
import os
import time
from pathlib import Path
import asyncio

import rich
from alist_sdk import Client

from alist_sync.alist_client import AlistClient
from alist_sync.config import cache_dir
from common import create_storage_local, clear_dir


WORKDIR = Path(__file__).parent
DATA_DIR = WORKDIR / "alist/test_dir"
DATA_DIR_DST = WORKDIR / "alist/test_dir_dst"
DATA_DIR_DST2 = WORKDIR / "alist/test_dir_dst2"

WORKDIR.joinpath("logs").mkdir(parents=True, exist_ok=True)

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(name)s %(levelname)s - %(message)s"},
        "systemd": {"format": "%(name)s %(levelname)s - %(message)s"},
        "error": {
            "format": (
                "TIME      = %(asctime)s \n"
                "FILE_NAME = %(filename)s \n"
                "FUNC_NAME = %(funcName)s \n"
                "LINE_NO   = %(lineno)d \n"
                "LEVEL     = %(levelname)s \n"
                "MESSAGE   = %(message)s \n"
                "EXCEPTION = %(exc_info)s \n"
                "+------------------------------------------+"
            )
        },
    },
    "handlers": {
        "console": {
            "class": "rich.logging.RichHandler",
            "formatter": "simple",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "simple",
            "level": "INFO",
            "filename": WORKDIR / "logs/debugger.log",
            "mode": "a+",
            "maxBytes": 50 * 1024**2,
            "backupCount": 5,
        },
        "file_warning": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "error",
            "level": "WARNING",
            "filename": WORKDIR / "logs/debugger-error.log",
            "mode": "a+",
            "maxBytes": 50 * 1024**2,
            "backupCount": 5,
        },
        "root_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": WORKDIR / "logs/root.log",
            "mode": "a+",
            "maxBytes": 50 * 1024**2,
            "backupCount": 5,
        },
    },
    "loggers": {
        "alist-sync": {
            "handlers": ["console", "file_warning"],
            "level": "DEBUG",
        },
        "alist-sdk": {
            "handlers": ["console", "file_warning"],
            "level": "DEBUG",
        },
    },
    "root": {
        "handlers": ["root_handler", "file_warning"],
        "level": "DEBUG",
    },
}

logging.config.dictConfig(log_config)


def setup_module():
    print("setup_module")
    os.system(f"bash {WORKDIR}/init_alist.sh")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR_DST.mkdir(parents=True, exist_ok=True)
    DATA_DIR_DST2.mkdir(parents=True, exist_ok=True)
    time.sleep(2)
    _client = Client(
        "http://localhost:5244", verify=False, username="admin", password="123456"
    )
    create_storage_local(_client, mount_name="/local", local_path=DATA_DIR)
    create_storage_local(_client, mount_name="/local_dst", local_path=DATA_DIR_DST)
    create_storage_local(_client, mount_name="/local_dst2", local_path=DATA_DIR_DST2)


def setup_function():
    print("setup_function")
    clear_dir(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    clear_dir(DATA_DIR_DST)
    DATA_DIR_DST.mkdir(parents=True, exist_ok=True)
    clear_dir(DATA_DIR_DST2)
    DATA_DIR_DST2.mkdir(parents=True, exist_ok=True)
    clear_dir(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)


setup_module()
setup_function()

items = [
    "test_scan_dir/a/a.txt",
    "test_scan_dir/b/b.txt",
    "test_scan_dir/c/c.txt",
    "test_scan_dir/d.txt",
    "e.txt",
]
items_2 = [
    "test_scan_dir/a/a.txt",
    "g.txt",
]
for i in items:
    Path(DATA_DIR / i).parent.mkdir(parents=True, exist_ok=True)
    Path(DATA_DIR / i).touch()

for i in items_2:
    Path(DATA_DIR_DST / i).parent.mkdir(parents=True, exist_ok=True)
    Path(DATA_DIR_DST / i).touch()


if __name__ == "__main__":
    from alist_sync.scanner import scan_dirs, Scanner

    client = AlistClient(
        base_url="http://localhost:5244",
        verify=False,
        username="admin",
        password="123456",
    )

    d: Scanner = asyncio.run(scan_dirs("/local", "/local_dst", client=client))
    rich.print(
        d.items,
    )
