#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : debugger_models.py
@Author     : LeeCQ
@Date-Time  : 2024/8/23 21:13
"""
import os
from pathlib import Path

os.chdir(Path(__file__).parent)
os.environ["ALIST_SYNC_CONFIG"] = "test_config.yaml"

from alist_sdk import AlistPath

from alist_sync.models import TransferLog


def transfer_log():
    log = TransferLog(
        transfer_type="upload",
        source_path=AlistPath("/test/test.txt"),
        target_path=AlistPath("/test/test.txt"),
        status="success",
        message="success",
    )
    log.set_id()
    return log.save()


a = transfer_log()
print(type(a))