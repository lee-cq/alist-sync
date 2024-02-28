#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : downloader.py
@Author     : LeeCQ
@Date-Time  : 2024/2/25 21:17

下载器使用一个单独线程启动，它创建一个事件循环并在其内部保持同步。
"""
import time
import urllib.parse
from typing import TYPE_CHECKING

from alist_sdk import AlistPath

from alist_sync.alist_client import create_async_client

if TYPE_CHECKING:
    ...


def upload_stream(source_path: AlistPath, target_path: AlistPath):
    async def main():
        async with create_async_client(source_path.client).stream(
            "GET", source_path.as_download_uri(), follow_redirects=True
        ) as stream_resp:
            return await create_async_client(target_path.client).put(
                "/api/fs/put",
                headers={
                    "As-Task": "false",
                    "Content-Type": "application/octet-stream",
                    "Last-Modified": str(int(time.time() * 1000)),
                    "File-Path": urllib.parse.quote_plus(str(target_path.as_posix())),
                },
                content=stream_resp.aiter_bytes(),
            )

    import asyncio

    return asyncio.run(main())
