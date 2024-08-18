#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : scanner.py
@Author     : LeeCQ
@Date-Time  : 2024/8/16 22:31
"""
from datetime import datetime
from typing import Iterator
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

from alist_sdk.path_lib import AlistPath

from models import File, Doer


def scan(path: AlistPath) -> Iterator[AlistPath]:
    """"""

    if Doer.get_or_none(abs_path=str(path)):
        return
    if path.is_file():
        yield path
    else:
        for p in path.iterdir():
            yield from scan(p)
    try:
        Doer(abs_path=str(path)).save(force_insert=True)
    except:
        pass


def path2file(p: AlistPath, ) -> File:
    return File(
        abs_path=p.as_posix(),
        parent=p.parent.as_posix(),
        mtime=p.stat().modified,
        hash=p.stat().hash_info or "",
        size=p.stat().size,
        update_time=datetime.now(),
        update_owner="scan",
    )


def scan_file(path: AlistPath) -> Iterator[File]:
    for p in scan(path):
        file = path2file(p)
        file.save()
        yield file


def scan_multi(path: AlistPath, threads=3, max_size=30) -> Iterator[AlistPath]:
    """多线程的扫描"""
    worker_count = 0

    def _scan(_path: AlistPath):
        if _path.is_file():
            _qu.put(_path)
            data["worker_count"] -= 1
        else:
            for _p in _path.iterdir():
                pool.submit(_scan, _p)
                data["worker_count"] += 1
        if data["worker_count"] == 0:
            _qu.put(None)

    data = {"worker_count": 0}
    pool = ThreadPoolExecutor(max_workers=threads)
    _qu = Queue(maxsize=max_size)
    pool.submit(_scan, path)
    while True:
        _d = _qu.get()
        if _d is None:
            pool.shutdown(wait=True)
            break
        yield _d


if __name__ == "__main__":
    from alist_sdk.path_lib import login_server
    from models import db
    import logging

    logger = logging.getLogger("peewee")
    logger.addHandler(logging.StreamHandler())
    logger.setLevel("DEBUG")

    db.connect()

    login_server(
        server="https://alist.leecq.cn",
        username="admin_test",
        password="alist_admin_test",
    )

    a = AlistPath("https://alist.leecq.cn/Drive-New/code/")
    print(list(scan_file(a)))
