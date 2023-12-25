#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_scanner.py
@Author     : LeeCQ
@Date-Time  : 2023/12/17 22:26

"""
from pathlib import Path

import asyncio

from alist_sync.alist_client import AlistClient
from .common import (
    DATA_DIR,
    DATA_DIR_DST,
    DATA_DIR_DST2,
    setup_module as _sm,
    setup_function as _sf,
)

from alist_sync.scanner import scan_dirs, Scanner

setup_module = _sm
setup_function = _sf


def test_scan_dir():
    items = [
        "test_scan_dir/a/a.txt",
        "test_scan_dir/b/b.txt",
        "test_scan_dir/c/c.txt",
        "test_scan_dir/d.txt",
        "e.txt",
        ".alist-sync-data/sync-locker.json",
        ".alist-sync-data/history/MD5.history",
        ".alist-sync-data/history/MD5.history.json"
    ]
    for i in items:
        Path(DATA_DIR.fs_path / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR.fs_path / i).touch()
        Path(DATA_DIR_DST.fs_path / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR_DST.fs_path / i).touch()
        Path(DATA_DIR_DST2.fs_path / i).parent.mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR_DST2.fs_path / i).touch()

    assert DATA_DIR_DST2.fs_path.joinpath(".alist-sync-data/sync-locker.json").exists()

    res = asyncio.run(
        scan_dirs(
            DATA_DIR.mount_path,
            DATA_DIR_DST.mount_path,
            DATA_DIR_DST2.mount_path,
            client=AlistClient(
                base_url="http://localhost:5244",
                verify=False,
                username="admin",
                password="123456",
            ),
        )
    )

    assert isinstance(res, Scanner)
    assert 'sync-locker.json' not in [_.name for _ in res.items.get(DATA_DIR_DST2.mount_path)]
    assert 'MD5.history' not in [_.name for _ in res.items.get(DATA_DIR_DST2.mount_path)]
