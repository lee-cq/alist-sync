#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : temp_files.py
@Author     : LeeCQ
@Date-Time  : 2024/3/23 14:02

"""
from pathlib import Path
from typing import Literal

from alist_sdk import AlistPathType, AlistPath
from pydantic import BaseModel

B = 1
KB = B * 1024
MB = KB * 1024
GB = MB * 1024


class TempFile(BaseModel):
    local_path: Path
    remote_path: AlistPathType
    status: Literal["init", "downloading", "downloaded", "failed", "removed"] = "init"
    refer_times: int = 1


class TempFiles(BaseModel):
    pre_size: int = 0
    tmp_files: dict[Path, TempFile] = {}

    def __del__(self):
        for fp in self.tmp_files.keys():
            fp.unlink(missing_ok=True)

    def add_tmp(self, path: Path, remote_file: str | AlistPath):
        if path in self.tmp_files:
            self.tmp_files[path].refer_times += 1
        self.tmp_files[path] = TempFile(
            local_path=path,
            remote_path=remote_file,
        )

    def done_tmp(self, path: Path):
        assert path in self.tmp_files, f"没有找到path: {path}"
        self.tmp_files[path].refer_times -= 1
        # if self.tmp_files[path] <= 0:
        #     self.clear_file(path)

    def clear_file(self, path: Path):
        path.unlink()
        del self.tmp_files[path]

    def pre_total_size(self):
        return sum(_.remote_path.stat().size for _ in self.tmp_files.values())

    def total_size(self):
        return sum(fp.stat().st_size for fp in self.tmp_files.keys() if fp.exists())

    def status(self) -> tuple[int, int, int, str]:
        """
        :return 总大小，总文件数，总引用数，message
        """
        _total_size = self.total_size()
        _files = len(self.tmp_files)
        _uses = sum(_.refer_times for _ in self.tmp_files.values())
        return (
            _total_size,
            _files,
            _uses,
            f"当前缓存了{_files} 个文件，占用空间{_total_size}, 被{_uses} Worker引用。",
        )

    def auto_clear(self):
        if self.total_size() < 10 * GB:
            return
        [
            self.clear_file(path)
            for path, t in self.tmp_files.items()
            if t.refer_times <= 0
        ]
        return self.auto_clear()
