#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : worker_manager.py
@Author     : LeeCQ
@Date-Time  : 2024/8/20 0:29
"""
import threading
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from alist_sync_new.checker import Checker
from alist_sync_new.config import SyncGroup
from alist_sync_new.worker import Worker


class WorkerManager:
    def __init__(self, sync_group: SyncGroup):
        self.sync_group = sync_group
        self.workers = ThreadPoolExecutor(max_workers=sync_group.max_workers)
        self.checker = Checker(sync_group.sync_type, *sync_group.sync_path)
        self.semaphore = threading.Semaphore(sync_group.max_workers + 1)

    def start(self):
        for worker in self.checker.iter_checker():
            if worker:
                self.workers.submit(self.run_worker, self.create_worker(worker))

    def stop(self):
        self.checker.stop()
        self.workers.shutdown(wait=False, cancel_futures=True)

    def create_worker(self, transfer_info):
        self.semaphore.acquire()
        return Worker()

    def run_worker(self, worker):
        try:
            worker.run()
        finally:
            self.semaphore.release()
