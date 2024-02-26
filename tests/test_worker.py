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


def test_worker():
    from pymongo import MongoClient
    from pymongo.server_api import ServerApi

    uri = (
        "mongodb+srv://alist-sync:alist-sync-p@a1.guggt7c.mongodb.net/alist_sync?"
        "retryWrites=true&w=majority&appName=A1"
    )

    client = MongoClient(uri, server_api=ServerApi("1"))
    w = Worker(
        owner="admin",
        type="delete",
        need_backup=True,
        backer_dir=AlistPath("http://localhost:5244/local/.history"),
        source_path="http://localhost:5244/local/test.txt",
        collection=client.get_default_database().get_collection("workers"),
    )
    print(w.update())


def test_workers():
    import os
    from pymongo import MongoClient
    from pymongo.server_api import ServerApi

    uri = os.environ["MONGODB_URI"]

    client = MongoClient(uri, server_api=ServerApi("1"))
    ws = Workers()
    ws.load_from_mongo()
