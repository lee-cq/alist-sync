#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : checker.py
@Author     : LeeCQ
@Date-Time  : 2024/8/17 15:16
"""

from typing import Iterator

from alist_sdk import AlistPath

from alist_sync_new import const
from alist_sync_new.models import File, TransferLog, Doer
from alist_sync_new.scanner import path2file, scan


class Checker:
    """若干个Path进行比对"""

    def __init__(self, sync_type: str, *path: AlistPath):
        self.sync_path = sync_type
        self.paths = path

        for p in self.paths:
            Doer.create_no_error(abs_path=p.joinpath(".alist-sync-backup"))

    def stop(self):
        pass

    def iter_check(self) -> Iterator[tuple[AlistPath, list[AlistPath]]]:
        if self.sync_path == const.SyncType.mirror:
            yield self.paths[0], self.paths[1:]
        elif self.sync_path == const.SyncType.copy:
            for p in self.paths:
                yield p, [_ for _ in self.paths if p != _]
        else:
            raise ValueError(
                f"unknown sync type: {self.sync_path} [{const.SyncType.str()}]"
            )

    def iter_checker(self):
        for m, ps in self.iter_check():
            yield from self.checker(m, ps)

    def checker(
        self,
        main_path: AlistPath,
        c_paths: list[AlistPath],
    ) -> Iterator[dict]:
        """检查器"""
        for file in scan(main_path):
            fi_info = path2file(file)
            db_info = File.get_or_none(abs_path=fi_info.abs_path)
            if db_info is not None and fi_info == db_info:
                # 文件内容没有变更，下一个
                continue
            relative = file.relative_to(main_path)
            for c in c_paths:
                abs_c = c.joinpath(relative)
                if not abs_c.exists():
                    yield dict(
                        transfer_type=const.TransferType.copy,
                        source_path=file,
                        target_path=abs_c,
                    )
