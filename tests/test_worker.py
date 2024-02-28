#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_worker.py
@Author     : LeeCQ
@Date-Time  : 2024/2/24 18:30
"""

import sys
import pytest

from alist_sdk.path_lib import PureAlistPath, AlistPath, login_server

from alist_sync.d_worker import Worker, Workers
from alist_sync.config import create_config

sync_config = create_config()


def test_worker_copy():
    docs = {
        # "_id": "013ac712314196a73bc97baba0e0cb97f769140b",
        "backup_dir": None,
        "created_at": "2024-02-27T15:32:54.287104",
        "error_info": None,
        "need_backup": False,
        "owner": "test",
        "source_path": "http://localhost:5244/local/test_dir/test/t1/test1.txt",
        "status": "init",
        "target_path": "http://localhost:5244/local_dst/test_dir/test/t1/test1.txt",
        "type": "copy",
    }
    login_server(
        **sync_config.get_server("http://localhost:5244/").dump_for_alist_path()
    )
    login_server(
        **sync_config.get_server("http://localhost:5244/").dump_for_alist_path()
    )
    worker = Worker(**docs)
    worker.run()
