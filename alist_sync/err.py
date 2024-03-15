#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : err.py
@Author     : LeeCQ
@Date-Time  : 2024/3/2 11:55

"""


class AlistSyncError(Exception):
    pass


class ScanerError(AlistSyncError):
    pass


class CheckerError(AlistSyncError):
    pass


class WorkerError(AlistSyncError):
    pass


class StatusError(AlistSyncError):
    """状态异常"""


class RetryError(WorkerError):
    pass


class DownloaderError(WorkerError):
    pass


class UploadError(WorkerError):
    pass


class RecheckError(WorkerError):
    pass
