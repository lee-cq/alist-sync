#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : worker_manager.py
@Author     : LeeCQ
@Date-Time  : 2024/8/20 0:29
"""
from concurrent.futures import ThreadPoolExecutor
import time
import logging

from alist_sync.checker import Checker
from alist_sync.config import SyncGroup
from alist_sync.worker import Worker

logger = logging.getLogger("alist-sync.manager")


class WorkerManager:
    def __init__(self, sync_group: SyncGroup):
        logger.info(f"New SyncGroup: {sync_group}")
        self.sync_group = sync_group
        self.workers = ThreadPoolExecutor(max_workers=sync_group.max_workers)
        self.checker = Checker(sync_group.sync_type, *sync_group.sync_path)

    def start(self):
        for worker in self.checker.iter_checker():
            if worker:
                while self.workers._work_queue.qsize() > self.sync_group.max_workers:
                    time.sleep(1)
                logger.info(f"new worker: {worker}")
                self.workers.submit(self.run_worker, self.create_worker(worker))

    def stop(self):
        self.checker.stop()
        self.workers.shutdown(wait=False, cancel_futures=True)

    def create_worker(self, transfer_info: dict) -> Worker:
        _w = Worker(**transfer_info)
        _w.backup_path = self.sync_group.get_backup_path(_w.target_path)
        return _w

    def run_worker(self, worker):
        try:
            worker.run()
        except Exception as e:
            logger.error(f"worker {worker.target_path} error: {e}")
        finally:
            pass
