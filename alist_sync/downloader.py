#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : downloader.py
@Author     : LeeCQ
@Date-Time  : 2024/2/25 21:17

下载器使用一个单独线程启动，它创建一个事件循环并在其内部保持同步。
"""
import os
from pathlib import Path
from typing import TYPE_CHECKING

from alist_sdk import AlistPath

if TYPE_CHECKING:
    ...


def find_aria2_bin(default=None):
    """"""
    paths = os.getenv("PATH").split(";" if os.name == "nt" else ":")
    for p in paths:
        p = Path(p)
        for i in p.glob("aria2c*"):
            if i.is_file():
                return i.resolve()
    if default:
        return default
    raise FileNotFoundError()


def make_aria2_cmd(
    remote: AlistPath | str,
    local: Path = None,
    headers: dict = None,
    aria2_bin: str | Path = None,
):
    """aria2命令构造器"""
    aria2_bin = aria2_bin or find_aria2_bin(default="../tmp/aria2c")
    headers = {k.lowwer(): v for k, v in headers.items()} if headers else {}
    ua = headers.pop(
        "user-agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    )

    _cmd = [
        aria2_bin,
        "-q",
        "-c",
        "-l",
        local.as_posix() + ".log",
        "--user-agent",
        ua,
        "-x",
        "5",
        *[f'--header="{k}: {v}" ' for k, v in headers.items()],
        "-o",
        str(local),
        remote.as_download_uri() if isinstance(remote, AlistPath) else remote,
    ]
    print(_cmd)
    return _cmd


def make_aria2_rpc(local: Path, remote: AlistPath | str, headers, *args, **kwargs):
    """"""


def start_aria2c_daemon():
    """
    https://www.jianshu.com/p/3c1b65907fb7
    """


async def aria2c(cmd: list):
    """"""
    from asyncio import create_subprocess_exec

    c = await create_subprocess_exec(*cmd)
    await c.communicate()
    return c.returncode


async def aria2(rpc: dict):
    """"""


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        aria2c(
            make_aria2_cmd(
                "https://licq.sharepoint.com/sites/shareDrive/_layouts/15/download.aspx?UniqueId=7dcd50f2-bca9-4fa7-9a67-8080c22622e5&Translate=false&tempauth=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAvbGljcS5zaGFyZXBvaW50LmNvbUA0YjhiYTQxMS00ZWEzLTRkYjItOTVlMC05MGYzMGNmNDYzYTciLCJpc3MiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAiLCJuYmYiOiIxNzEwNjAwODY5IiwiZXhwIjoiMTcxMDYwNDQ2OSIsImVuZHBvaW50dXJsIjoiK0E5eHRnb2MxRjNHSnU5QWNZM09jdWVMY0puV3ArTXBzZ3VYczR2dzh0az0iLCJlbmRwb2ludHVybExlbmd0aCI6IjEzMiIsImlzbG9vcGJhY2siOiJUcnVlIiwiY2lkIjoicWNodkdHeHNEMEdrQzZZamE4SVpzdz09IiwidmVyIjoiaGFzaGVkcHJvb2Z0b2tlbiIsInNpdGVpZCI6IllUZGpZV0kzT0dFdE9UZzVNUzAwWXpFMUxUbG1NbVl0T1RnMFlqSTVNRFF5T0dNeiIsImFwcF9kaXNwbGF5bmFtZSI6ImFsaXN0IiwiZ2l2ZW5fbmFtZSI6Iui2hee-pCIsInNpZ25pbl9zdGF0ZSI6IltcImttc2lcIl0iLCJhcHBpZCI6ImE3NzNjNzhkLTIwNTYtNGNiYS05NmNmLTQ2Y2UwODI2OTBmYiIsInRpZCI6IjRiOGJhNDExLTRlYTMtNGRiMi05NWUwLTkwZjMwY2Y0NjNhNyIsInVwbiI6ImxjcUBsZWVjcS5jbiIsInB1aWQiOiIxMDAzMjAwMTVFMTMwM0NBIiwiY2FjaGVrZXkiOiIwaC5mfG1lbWJlcnNoaXB8MTAwMzIwMDE1ZTEzMDNjYUBsaXZlLmNvbSIsInNjcCI6ImFsbGZpbGVzLndyaXRlIG15YXBwZm9sZGVyLndyaXRlIGFsbHByb2ZpbGVzLnJlYWQiLCJ0dCI6IjIiLCJpcGFkZHIiOiIyMC4xOTAuMTQ0LjE3MSJ9.oGks_Ait_SC_x9cIb9m5-7su5-jll99oFBM6jhk9SHY&ApiVersion=2.0",
                Path("test.ttt"),
            )
        )
    )
