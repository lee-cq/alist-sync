#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_models.py
@Author     : LeeCQ
@Date-Time  : 2024/8/23 21:01
"""
import os
from pathlib import Path

os.chdir(Path(__file__).parent)
os.environ["ALIST_SYNC_CONFIG"] = "test_config.yaml"

from alist_sdk import AlistPath

from alist_sync.models import TransferLog


def transfer_log():
    log = TransferLog(
        source_path=AlistPath("/test/test.txt"),
        target_path=AlistPath("/test/test.txt"),
        status="success",
        message="success",
    )
    log.set_id()
    log.save()


transfer_log()