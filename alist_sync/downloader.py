#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : downloader.py
@Author     : LeeCQ
@Date-Time  : 2024/2/25 21:17

下载器使用一个单独线程启动，它创建一个事件循环并在其内部保持同步。
"""
import queue
import time
import urllib.parse
from typing import TYPE_CHECKING

from alist_sdk import AlistPath

from alist_sync.alist_client import create_async_client, AlistClient

if TYPE_CHECKING:
    ...


def upload_stream(source_path: AlistPath, target_path: AlistPath):
    import asyncio

    _queue = asyncio.Queue()

    # noinspection PyArgumentList
    async def put_stream():
        _c: AlistClient = create_async_client(source_path.client)
        async with _c.stream(
            "GET",
            source_path.as_download_uri(),
            follow_redirects=True,
        ) as stream_resp:
            async for chunk in stream_resp.aiter_bytes():
                print("Put Chunk size:", len(chunk), "bytes.")
                await _queue.put(chunk)
            else:
                await _queue.put(None)

    async def put_test():
        a = open("/Users/lcq/Downloads/drunbility.pdf", "rb")
        while True:
            chunk = a.read(1024)
            if not chunk:
                await _queue.put(None)
                break
            await _queue.put(chunk)

    async def get_chunk():
        while True:
            chunk = await _queue.get()
            if chunk is None:
                break
            yield chunk

    # noinspection PyAsyncCall
    async def main():

        asyncio.create_task(put_test())
        return await create_async_client(target_path.client).put(
            "/api/fs/put",
            headers={
                "As-Task": "false",
                "Content-Type": "application/octet-stream",
                "Last-Modified": str(int(time.time() * 1000)),
                "File-Path": urllib.parse.quote_plus(str(target_path.as_posix())),
            },
            content=get_chunk(),
        )

    return asyncio.run(main())


def upload_stream_thread(source_path: AlistPath, target_path: AlistPath):
    """"""

    def put_stream():
        with source_path.client.stream(
            "GET", source_path.as_download_uri(), follow_redirects=True
        ) as stream_resp:
            total = 0
            for i in stream_resp.iter_bytes():
                total += len(i)
                print("Download Chunk size:", total, "bytes.")
                _queue.put(i)

            print("None Putted")
            _queue.put(None)

    def get_chunk():
        total = 0
        while True:
            chunk = _queue.get()
            if chunk is None:
                print("None Got")
                break
            total += len(chunk)
            print(f"\rupload Chunk size: {total} bytes. [{time.time()}]", end="")
            yield chunk

    import threading

    _queue = queue.Queue()

    threading.Thread(target=put_stream).start()
    print("启动线程")
    return target_path.client.put(
        "/api/fs/put",
        timeout=0,
        headers={
            "As-Task": "false",
            "Content-Type": "application/octet-stream",
            "Last-Modified": str(int(time.time() * 1000)),
            "File-Path": urllib.parse.quote_plus(str(target_path.as_posix())),
        },
        # content=open("/Users/lcq/Movies/志愿军-雄军出击-含广告.mp4", "rb"),
        content=get_chunk(),
    )




if __name__ == "__main__":
    from alist_sync.config import create_config, AlistServer
    from alist_sdk import login_server

    import logging

    logging.basicConfig(level=logging.DEBUG)

    sync_config = create_config()
    for _ in sync_config.alist_servers:
        _: AlistServer
        login_server(**_.dump_for_alist_path())

    source = AlistPath("https://alist.leecq.cn/local/Country.mmdb")
    target = AlistPath("http://localhost:5244/local/Country.mmdb")

    print(source.stat())
    # a = upload_stream_thread(source, target)
    a = upload_big_file(target)
    print(a.text)
