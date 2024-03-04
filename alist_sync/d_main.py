#!/bin/env python3
"""

"""
import fnmatch
import logging
import threading
import time
from functools import lru_cache
from queue import Queue
from typing import Callable

import alist_sdk

from alist_sdk import AlistPath, login_server

from alist_sync.d_worker import Workers
from alist_sync.thread_pool import MyThreadPoolExecutor
from alist_sync.config import SyncGroup, create_config, AlistServer
from alist_sync.d_checker import get_checker

sync_config = create_config()
logger = logging.getLogger("alist-sync.main")


def login_alist(server: AlistServer):
    """"""
    _c = login_server(**server.dump_for_alist_path())
    logger.info("Login: %s[%s] Success.", _c.base_url, _c.login_username)


def _make_ignore(_sync_group):
    @lru_cache(64)
    def split_path(_sync_group, path: AlistPath) -> tuple[AlistPath, str]:
        """将Path切割为sync_dir和相对路径"""
        for sr in _sync_group.group:
            try:
                return sr, path.relative_to(sr)
            except ValueError:
                pass
        raise ValueError()

    def __ignore(relative_path) -> bool:
        _, relative_path = split_path(_sync_group, relative_path)
        for _i in _sync_group.blacklist:
            if fnmatch.fnmatchcase(relative_path, _i):
                logger.debug("Ignore: %s, [matched: %s]", relative_path, _i)
                return True
        return False

    return __ignore


def scaner(url: AlistPath, _queue, i_func: Callable[[str | AlistPath], bool] = None):
    def _scaner(_url: AlistPath, _s_num):
        """ """
        if i_func is not None and i_func(url):
            return
        _s_num.append(1)
        logger.debug(f"Scaner: {_url}")
        try:
            for item in _url.iterdir():
                if item.is_file():
                    logger.debug(f"Find File: {item}")
                    _queue.put(item)
                elif item.is_dir():
                    pool.submit(_scaner, item, _s_num)
        except alist_sdk.AlistError:
            pass
        except Exception:
            _s_num.pop()

    assert url.exists(), f"目录不存在{url.as_uri()}"

    s_sum = []
    with MyThreadPoolExecutor(5, thread_name_prefix=f"scaner_{url.as_uri()}") as pool:
        pool.submit(_scaner, url, s_sum)
        while s_sum:
            time.sleep(2)


def checker(sync_group: SyncGroup, _queue_worker: Queue) -> threading.Thread | None:
    """"""
    if sync_group.enable is False:
        logger.warning("Checker: %s is disable", sync_group.name)
        return

    logger.info("Checker: %s", sync_group.name)

    for uri in sync_group.group:
        login_alist(sync_config.get_server(uri.as_uri()))

    _queue_scaner = Queue(30)
    _scaner_pool = MyThreadPoolExecutor(5, "scaner_")

    _ct = get_checker(sync_group.type)(sync_group, _queue_scaner, _queue_worker).start()

    _sign = ["copy"]
    __ignore = _make_ignore(sync_group)
    if sync_group.type in _sign:
        logger.debug(f"Copy 只需要扫描 {sync_group.group[0].as_uri() = }")
        scaner(sync_group.group[0], _queue_scaner, __ignore)
    else:
        for uri in sync_group.group:
            scaner(uri, _queue_scaner, __ignore)

    return _ct


def main():
    """"""
    _queue_worker = Queue(30)
    _tw = Workers().start(_queue_worker)

    for sync_group in sync_config.sync_groups:
        checker(sync_group, _queue_worker)

    _tw.join()


def main_debug():
    """"""

    _tw = Workers()

    def iter_file(url, i_func: Callable[[str], bool] | None = None):
        if i_func is not None and i_func(url):
            return

        if url.is_file():
            yield url
        elif url.is_dir():
            for item in url.iterdir():
                yield from iter_file(item, i_func)
        else:
            logger.warning("未知的文件类型: %s", url)

    for sync_group in sync_config.sync_groups:
        _check = get_checker(sync_group.type)(sync_group, Queue(1), Queue(1))
        _ignore = _make_ignore(sync_group)
        if sync_group.enable is False:
            logger.warning("Checker: %s is disable", sync_group.name)
            continue
        for uri in sync_group.group:
            login_alist(sync_config.get_server(uri.as_uri()))

        for _file in iter_file(sync_group.group[0], _ignore):
            logger.debug(f"find file: {_file}")
            for _worker in _check.checker_every_dir(_file):
                if _worker is None:
                    continue
                logger.debug(f"Worker[{_worker.short_id}]:")
                _worker.run()


if __name__ == "__main__":
    main()
