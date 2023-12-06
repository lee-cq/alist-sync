# coding: utf8
"""增量的复制

基于配置文件的复制



"""
import asyncio


class SyncIncr:

    def __init__(self, alist_info, config_dir, cache_dir, sync_group):
        self.sync_group = sync_group
        self.cache_dir = cache_dir
        self.config_dir = config_dir
        self.alist_info = alist_info

    def run(self):
        asyncio.run(self.async_run())

    async def async_run(self):
        pass
