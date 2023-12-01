import os
import time
from pathlib import Path

import asyncio
import pytest

from alist_sdk import Client, Item, AsyncClient
from alist_sync.models import AlistServer, SyncDir
from alist_sync.scan_dir import scan_dir
from alist_sync.run_copy import CopyToTarget

from .common import create_storage_local, clear_dir

WORKDIR = Path(__file__).parent
DATA_DIR = WORKDIR / "alist/test_dir"
DATA_DIR_DST = WORKDIR / "alist/test_dir_dst"


def setup_module():
    print("setup_module")
    os.system(f'bash {WORKDIR}/init_alist.sh')
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR_DST.mkdir(parents=True, exist_ok=True)
    time.sleep(2)
    _client = Client('http://localhost:5244', verify=False, username='admin', password='123456')
    create_storage_local(
        _client,
        mount_name="/local",
        local_path=DATA_DIR
    )
    create_storage_local(
        _client,
        mount_name="/local_dst",
        local_path=DATA_DIR_DST
    )


def setup_function():
    print("setup_function")
    clear_dir(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    clear_dir(DATA_DIR_DST)
    DATA_DIR_DST.mkdir(parents=True, exist_ok=True)


def test_scan_dir():
    items = [
        "test_scan_dir/a/a.txt",
        "test_scan_dir/b/b.txt",
        "test_scan_dir/c/c.txt",
        "test_scan_dir/d.txt",
        "e.txt",
    ]
    for i in items:
        Path(DATA_DIR / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR / i).touch()

    res = asyncio.run(
        scan_dir(
            AsyncClient(base_url='http://localhost:5244', verify=False, username='admin', password='123456'),
            "/local"
        )
    )

    assert isinstance(res, SyncDir)
    assert res.base_path == "/local"
    assert isinstance(res.items, list)
    assert res.items.__len__() == len(items)
    assert isinstance(res.items[0], Item)
    assert {i.full_name.as_posix() for i in res.items} == {f"/local/{i}" for i in items}


def test_run_copy():
    items = [
        "test_scan_dir/a/a.txt",
        "test_scan_dir/b/b.txt",
        "test_scan_dir/c/c.txt",
        "test_scan_dir/d.txt",
        "e.txt",
    ]
    for i in items:
        Path(DATA_DIR / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR / i).touch()

    res = asyncio.run(
        CopyToTarget(AlistServer(base_url='http://localhost:5244', verify=False, username='admin', password='123456'), copy,
                     mirror, sync, sync - mult, source_dir="/local", target_path=["/local_dst"]).async_run()
    )
    assert DATA_DIR_DST.joinpath("test_scan_dir/a/a.txt").exists()
