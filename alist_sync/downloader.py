#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : downloader.py
@Author     : LeeCQ
@Date-Time  : 2024/2/25 21:17

下载器使用一个单独线程启动，它创建一个事件循环并在其内部保持同步。
"""

from pathlib import Path
from typing import TYPE_CHECKING

from alist_sdk import AlistPath

if TYPE_CHECKING:
    ...


def find_aria2_bin():
    """"""


def make_aria2_cmd(
    remote: AlistPath | str,
    local: Path = None,
    headers: dict = None,
    aria2_bin: str | Path = None,
):
    """aria2命令构造器"""
    aria2_bin = aria2_bin or "../tmp/aria2c"
    headers = {k.lowwer(): v for k, v in headers.items()} if headers else {}
    headers.setdefault("ua", "")  # TODO

    _cmd = [
        aria2_bin,
        "-c",
        "-x",
        "5",
        *[f'--header="{k}: {v}" ' for k, v in headers.items()],
        "-o",
        local,
        remote.as_download_uri() if isinstance(remote, AlistPath) else remote,
    ]
    print(_cmd)
    return _cmd


def make_aria2_rpc(local: Path, remote: AlistPath | str, headers, *args, **kwargs):
    """"""


def start_aria2c_daemon():
    """"""


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
                "https://alist.leecq.cn/d/%E7%A7%BB%E5%8A%A8%E4%BA%91%E7%9B%98/Music/song/A-Lin-%E5%A4%A9%E8%8B%A5%E6%9C%89%E6%83%85.mp3",
                Path("test.mp3"),
            )
        )
    )
