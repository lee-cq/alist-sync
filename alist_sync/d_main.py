#!/bin/env python3
"""

"""
import logging
import threading
import time
from queue import Queue

from alist_sdk import AlistPath, login_server
from alist_sdk.path_lib import ALIST_SERVER_INFO

from alist_sync.d_worker import Workers
from alist_sync.thread_pool import MyThreadPoolExecutor
from alist_sync.config import SyncGroup, create_config, AlistServer
from alist_sync.d_checker import get_checker

sync_config = create_config()
logger = logging.getLogger("alist-sync.main")


def login_alist(server: AlistServer):
    """"""
    if server.base_url in ALIST_SERVER_INFO:
        return
    login_server(**server.dump_for_alist_path())
    server.token = ALIST_SERVER_INFO.get(server.base_url)
    logger.info("Login: %s Success.", server.base_url)


def scaner(url: AlistPath, _queue):
    def _scaner(_url: AlistPath, _s_num):
        """ """
        _s_num.append(1)
        logger.debug(f"Scaner: {_url}")
        try:
            for item in _url.iterdir():
                if item.is_file():
                    logger.debug(f"find file: {item}")
                    _queue.put(item)
                elif item.is_dir():
                    pool.submit(_scaner, item, _s_num)
        finally:
            _s_num.pop()

    s_sum = []
    pool = MyThreadPoolExecutor(5)
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
    if sync_group.type in _sign:
        scaner(sync_group.group[0], _queue_scaner)
    else:
        for uri in sync_group.group:
            scaner(uri, _queue_scaner)

    return _ct


def main():
    """"""
    _queue_worker = Queue(30)
    _tw = Workers().start(_queue_worker)

    for sync_group in sync_config.sync_groups:
        checker(sync_group, _queue_worker)

    _tw.join()


if __name__ == "__main__":
    logger_alist_sync = logging.getLogger("alist-sync")
    logger_alist_sync.setLevel(logging.DEBUG)
    logger_alist_sync.addHandler(logging.StreamHandler())
    logger.info("Begin...")
    main()
