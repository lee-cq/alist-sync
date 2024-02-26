#!/bin/env python3
"""

"""
import queue
import threading
from queue import Queue
from alist_sync.thread_pool import MyThreadPoolExecutor

from alist_sdk import AlistPath, login_server
from alist_sdk.path_lib import ALIST_SERVER_INFO

from alist_sync.config import SyncGroup, create_config, AlistServer
from alist_sync.d_checker import Checker

sync_config = create_config()


queue_checker = Queue()
queue_worker = Queue()


def login_alist(server: AlistServer):
    """"""
    login_server(**server.dump_for_sdk())
    server.token = ALIST_SERVER_INFO.get(server.base_url)


def scaner(url: AlistPath, _queue):
    def _scaner(_url: AlistPath):
        """"""
        for item in _url.iterdir():
            if item.is_file():
                _queue.put(item)
            elif item.is_dir():
                pool.submit(_scaner, item)

    pool = MyThreadPoolExecutor(5)
    pool.submit(_scaner, url)
    pool.wait()


def checker(sync_group: SyncGroup, _queue: Queue):
    """"""
    if sync_group.enable is False:
        return

    for uri in sync_group.group:
        login_alist(sync_config.get_server(uri))

    _queue_scaner = Queue(30)
    _scaner_pool = MyThreadPoolExecutor(5, "scaner_")

    _sign = ["copy", "mirror"]

    if sync_group.type in _sign:
        scaner(sync_group.group[0], _queue_scaner)
    else:
        for uri in sync_group.group:
            scaner(uri, _queue_scaner)

    return Checker(sync_group, _queue_scaner, _queue).mian()  # main()是死循环


def mian():
    """"""
