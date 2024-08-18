#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : const.py
@Author     : LeeCQ
@Date-Time  : 2024/8/17 17:35
"""


class _Base:
    @classmethod
    def str(cls) -> str:
        return "allow: " + ", ".join(
            v for k, v in cls.__dict__.items() if not k.startswith("__")
        )


class SyncType(_Base):
    copy = "copy"
    mirror = "mirror"


class TransferType(_Base):
    copy = "copy"
    delete = "delete"


class TransferStatus(_Base):
    init = "init"
    backed_up = "backed_up"
    coping = "coping"

    error = "error"
