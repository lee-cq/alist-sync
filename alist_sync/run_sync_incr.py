# coding: utf8
"""增量的复制

基于配置文件的复制

"""
import asyncio
import atexit
import json
import time
from threading import Thread
from pathlib import PurePosixPath

from alist_sync.base_sync import SyncBase
from alist_sync.config import AlistServer


class SyncIncr(SyncBase):
    path_data = '.alist-sync-data/'
    history_path = '.alist-sync-data/history/'
    locker_name = "locker.json"
    last_status_name = "last_status.json"

    def __init__(self, alist_info: AlistServer, config_dir, cache_dir, sync_group):
        super().__init__(alist_info, sync_group)

        self.sync_group = sync_group
        self.cache_dir = cache_dir
        self.config_dir = config_dir
        atexit.register(self.on_exit)

    def on_exit(self):
        """onexit"""
        for _ in self.sync_group:
            Thread(target=self._client.remove, args=(
                PurePosixPath(_).joinpath(self.path_data),
                self.locker_name,
            )).start()

    async def create_locker(self):
        """"""

        async def _locker(_dir):
            while True:
                if self.client.close():
                    break
                await self.client.upload_file_put(
                    json.dumps({
                        "sync_group": self.sync_group,
                        "update_time": int(time.time())
                    }).encode(),
                    PurePosixPath(_dir).joinpath(self.path_data).joinpath(self.locker_name),
                    as_task=False
                )
                await asyncio.sleep(60)

        for _ in self.sync_group:
            asyncio.create_task(
                _locker(_),
                name=f'alist-sync-locker_{_}'
            )

    async def async_run(self):
        await super().async_run()
        await self.create_locker()
