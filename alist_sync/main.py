#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : main.py
@Author     : LeeCQ
@Date-Time  : 2024/8/19 0:20
"""

import atexit
import logging
import os

from alist_sync.const import Env


logger = logging.getLogger("alist-sync.main")


def copy():
    from alist_sync.config import config
    from alist_sync.worker_manager import WorkerManager

    for sg in config.sync_groups:
        logger.info(f"Start Sync Group: {sg.name}")
        WorkerManager(sg).start()  # TODO 线程
