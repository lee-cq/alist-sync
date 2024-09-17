#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : scanner.py
@Author     : LeeCQ
@Date-Time  : 2024/8/16 22:31
"""
import logging
import time
from datetime import datetime
from typing import Iterator
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

from alist_sdk import HashInfo
from alist_sdk.path_lib import AlistPath
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from alist_sync.models import File, Doer, Index

logger = logging.getLogger("alist-sync.scanner")


def scan(path: AlistPath) -> Iterator[AlistPath]:
    """"""

    if Doer.get_or_none(abs_path=str(path)):
        logger.info(f"跳过目录: {path}")
        return

    if path.is_file():
        logger.debug(f"Find File: {path}")
        yield path
    else:
        logger.debug(f"递归目录: {path}")
        for p in path.iterdir():
            yield from scan(p)

    Doer.create_no_error(abs_path=str(path))


def path2file(p: AlistPath) -> File:
    return File(
        abs_path=p.as_uri(),
        parent=p.parent.as_uri(),
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
    yield None


def path2index(p: AlistPath) -> Index:
    return Index(
        abs_path=p.as_uri(),
        parent=p.parent.as_uri(),
        mtime=p.stat().modified,
        hash=(p.stat().hash_info or HashInfo()).model_dump_json(),
        size=p.stat().size,
        update_time=datetime.now(),
    )


def index_file(path: AlistPath, threads=3, max_size=30) -> None:
    """多线程的索引"""
    log = logging.getLogger("alist-sync.index_file")
    from alist_sync.config import engine
    from threading import Semaphore

    sem = Semaphore(max_size)

    def _scan(_path: AlistPath):
        with Session(engine) as session, sem:
            try:
                if _path.is_file():
                    log.debug(f"索引文件: {_path}")
                    session.add(path2index(_path))
                else:
                    log.debug(f"扫描目录: {_path}")
                    for _p in _path.iterdir():
                        log.debug(f"Add Index: {_p}")
                        session.add(path2index(_p))
                        if _p.is_dir():
                            pool.submit(_scan, _p)
                            data["worker_count"] += 1

            except Exception as e:
                log.exception(f"索引文件出错: {_path}, {e}")
            finally:
                try:
                    log.debug(f"提交事务: {_path}")
                    session.commit()
                    log.debug(f"索引文件完成: {_path}")

                except OperationalError:
                    log.error(f"数据库操作出错: {_path}")
                    pass
                except Exception as e:
                    log.exception(f"提交事务出错: {_path}, {e}")
                finally:
                    session.close()

                data["worker_count"] -= 1

    data = {"worker_count": 0}
    pool = ThreadPoolExecutor(max_workers=threads)
    pool.submit(_scan, path)
    while True:
        time.sleep(3)
        log.debug(f"并行线程: {data['worker_count']}")
        if data["worker_count"] <= 0:
            pool.shutdown(wait=True)
            break



