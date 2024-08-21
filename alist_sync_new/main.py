#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : main.py
@Author     : LeeCQ
@Date-Time  : 2024/8/19 0:20
"""


def copy():
    from alist_sync_new.config import config
    from alist_sync_new.worker_manager import WorkerManager

    for sg in config.sync_groups:
        WorkerManager(sg).start()  # TODO 线程
