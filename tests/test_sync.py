import os
import time
from pathlib import Path

import asyncio
import pytest

from alist_sdk import Client, Item, AsyncClient
from alist_sync.models import AlistServer, SyncDir
from alist_sync.scan_dir import scan_dir
from alist_sync.run_copy import CopyToTarget
from alist_sync.run_mirror import Mirror
from alist_sync.config import cache_dir

from .common import create_storage_local, clear_dir

WORKDIR = Path(__file__).parent
DATA_DIR = WORKDIR / "alist/test_dir"
DATA_DIR_DST = WORKDIR / "alist/test_dir_dst"
DATA_DIR_DST2 = WORKDIR / "alist/test_dir_dst2"


def setup_module():
    print("setup_module")
    os.system(f'bash {WORKDIR}/init_alist.sh')
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR_DST.mkdir(parents=True, exist_ok=True)
    DATA_DIR_DST2.mkdir(parents=True, exist_ok=True)
    time.sleep(2)
    _client = Client('http://localhost:5244', verify=False,
                     username='admin', password='123456')
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
    create_storage_local(
        _client,
        mount_name="/local_dst2",
        local_path=DATA_DIR_DST2
    )


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
            AsyncClient(base_url='http://localhost:5244',
                        verify=False, username='admin', password='123456'),
            "/local"
        )
    )

    assert isinstance(res, SyncDir)
    assert res.base_path == "/local"
    assert isinstance(res.items, list)
    assert res.items.__len__() == len(items)
    assert isinstance(res.items[0], Item)
    assert {i.full_name.as_posix() for i in res.items} == {
        f"/local/{i}" for i in items}


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
        CopyToTarget(
            AlistServer(base_url='http://localhost:5244',
                        verify=False,
                        username='admin',
                        password='123456'),
            source_path="/local",
            targets_path=["/local_dst", '/local_dst2']
        ).async_run()
    )
    assert DATA_DIR_DST.joinpath("test_scan_dir/a/a.txt").exists()
    assert DATA_DIR_DST2.joinpath("test_scan_dir/a/a.txt").exists()


def test_mirror():
    """测试镜像复制"""
    items_sou = {
        "test_scan_dir/a/a.txt",
        "test_scan_dir/b/b.txt",
        "test_scan_dir/c/c.txt",
        "test_scan_dir/d.txt",
        "e.txt",
    }
    items_tar1 = {
        "test_scan_dir/a/a.txt",
        "tar1/b.txt",
        "f.txt"
    }
    items_tar2 = {
        "tar2/g.txt",
        'g.txt',
    }

    for i in items_sou:
        Path(DATA_DIR / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR / i).touch()
    for i in items_tar1:
        Path(DATA_DIR_DST / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR_DST / i).touch()
    for i in items_tar2:
        Path(DATA_DIR_DST2 / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR_DST2 / i).touch()

    assert not DATA_DIR_DST.joinpath("test_scan_dir/b/b.txt").exists()
    assert not DATA_DIR_DST2.joinpath("test_scan_dir/b/b.txt").exists()

    assert DATA_DIR_DST.joinpath("tar1/b.txt").exists()
    assert DATA_DIR_DST.joinpath("f.txt").exists()

    assert DATA_DIR_DST2.joinpath("tar2/g.txt").exists()
    assert DATA_DIR_DST2.joinpath("g.txt").exists()

    asyncio.run(
        Mirror(
            AlistServer(
                base_url='http://localhost:5244',
                verify=False,
                username='admin',
                password='123456'),
            source_path="/local",
            targets_path=["/local_dst", "/local_dst2"]
        ).async_run()
    )

    assert DATA_DIR_DST.joinpath("test_scan_dir/a/a.txt").exists()
    assert DATA_DIR_DST2.joinpath("test_scan_dir/a/a.txt").exists()

    assert not DATA_DIR_DST.joinpath("tar1/b.txt").exists()
    assert not DATA_DIR_DST.joinpath("f.txt").exists()

    assert not DATA_DIR_DST2.joinpath("tar2/g.txt").exists()
    assert not DATA_DIR_DST2.joinpath("g.txt").exists()
