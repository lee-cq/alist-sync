from pathlib import Path

import asyncio

from alist_sdk import Item

from alist_sync.alist_client import AlistClient
from alist_sync.models import AlistServer
from alist_sync.scanner import scan_dirs, Scanner
from alist_sync.run_copy import Copy
from alist_sync.run_mirror import Mirror

from .common import (
    DATA_DIR,
    DATA_DIR_DST,
    DATA_DIR_DST2,
    setup_module,
    setup_function,
)


def test_scan_dir():
    items = [
        "test_scan_dir/a/a.txt",
        "test_scan_dir/b/b.txt",
        "test_scan_dir/c/c.txt",
        "test_scan_dir/d.txt",
        "e.txt",
    ]
    for i in items:
        Path(DATA_DIR.fs_path / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR.fs_path / i).touch()

    res = asyncio.run(
        scan_dirs("/local", client=AlistClient(
            base_url="http://localhost:5244",
            verify=False,
            username="admin",
            password="123456",
        ))
    )

    assert isinstance(res, Scanner)
    assert DATA_DIR.mount_path in res.items
    assert isinstance(res.items, dict)
    assert isinstance(res.items[DATA_DIR.mount_path], list)
    assert res.items[DATA_DIR.mount_path].__len__() == len(items)
    assert isinstance(res.items[DATA_DIR.mount_path][0], Item)
    assert {i.full_name.as_posix() for vs in res.items.values() for i in vs} == {
        f"{DATA_DIR.mount_path}/{i}" for i in items
    }


def test_run_copy():
    items = [
        "test_scan_dir/a/a.txt",
        "test_scan_dir/b/b.txt",
        "test_scan_dir/c/c.txt",
        "test_scan_dir/d.txt",
        "e.txt",
    ]
    for i in items:
        Path(DATA_DIR.fs_path / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR.fs_path / i).touch()

    asyncio.run(
        Copy(
            AlistServer(
                base_url="http://localhost:5244",
                verify=False,
                username="admin",
                password="123456",
            ),
            source_path="/local",
            targets_path=["/local_dst", "/local_dst2"],
        ).async_run()
    )
    assert DATA_DIR_DST.fs_path.joinpath("test_scan_dir/a/a.txt").exists()
    assert DATA_DIR_DST2.fs_path.joinpath("test_scan_dir/a/a.txt").exists()


def test_mirror():
    """测试镜像复制"""
    items_sou = {
        "test_scan_dir/a/a.txt",
        "test_scan_dir/b/b.txt",
        "test_scan_dir/c/c.txt",
        "test_scan_dir/d.txt",
        "e.txt",
    }
    items_tar1 = {"test_scan_dir/a/a.txt", "tar1/b.txt", "f.txt"}
    items_tar2 = {
        "tar2/g.txt",
        "g.txt",
    }

    for i in items_sou:
        Path(DATA_DIR.fs_path / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR.fs_path / i).touch()
    for i in items_tar1:
        Path(DATA_DIR_DST.fs_path / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR_DST.fs_path / i).touch()
    for i in items_tar2:
        Path(DATA_DIR_DST2.fs_path / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR_DST2.fs_path / i).touch()

    assert not DATA_DIR_DST.fs_path.joinpath("test_scan_dir/b/b.txt").exists()
    assert not DATA_DIR_DST2.fs_path.joinpath("test_scan_dir/b/b.txt").exists()

    assert DATA_DIR_DST.fs_path.joinpath("tar1/b.txt").exists()
    assert DATA_DIR_DST.fs_path.joinpath("f.txt").exists()

    assert DATA_DIR_DST2.fs_path.joinpath("tar2/g.txt").exists()
    assert DATA_DIR_DST2.fs_path.joinpath("g.txt").exists()

    asyncio.run(
        Mirror(
            AlistServer(
                base_url="http://localhost:5244",
                verify=False,
                username="admin",
                password="123456",
            ),
            source_path=DATA_DIR.mount_path,
            targets_path=[DATA_DIR_DST.mount_path, DATA_DIR_DST2.mount_path],
        ).async_run()
    )

    assert DATA_DIR_DST.fs_path.joinpath("test_scan_dir/a/a.txt").exists()
    assert DATA_DIR_DST2.fs_path.joinpath("test_scan_dir/a/a.txt").exists()

    assert not DATA_DIR_DST.fs_path.joinpath("tar1/b.txt").exists()
    assert not DATA_DIR_DST.fs_path.joinpath("f.txt").exists()

    assert not DATA_DIR_DST2.fs_path.joinpath("tar2/g.txt").exists()
    assert not DATA_DIR_DST2.fs_path.joinpath("g.txt").exists()
