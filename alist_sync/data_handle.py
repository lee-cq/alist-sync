#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : data_handle.py
@Author     : LeeCQ
@Date-Time  : 2024/2/27 22:15

"""
import abc
import datetime
import logging
import shelve
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from alist_sdk import AlistPath

if TYPE_CHECKING:
    from alist_sync.d_worker import Worker
    from pymongo.database import Database
    from pymongo.collection import Collection

logger = logging.getLogger("alist-sync.data_handle")


class HandleBase(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def update_worker(self, worker: "Worker", *field):
        """更新或创建Worker"""
        raise NotImplementedError

    @abc.abstractmethod
    def delete_worker(self, worker_id: str):
        """删除Worker"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_worker(self, worker_id: str):
        """获取Worker"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_workers(self, query=None) -> Iterable["Worker"]:
        """获取Workers"""
        raise NotImplementedError

    @abc.abstractmethod
    def load_locker(self) -> set["AlistPath"]:
        """加载锁"""
        raise NotImplementedError

    @abc.abstractmethod
    def path_in_workers(self, path: "AlistPath") -> bool:
        """判断路径是否在Worker中"""
        raise NotImplementedError

    def get_locker(self, path: "AlistPath"):
        """获取锁"""
        return self.path_in_workers(path)

    @abc.abstractmethod
    def update_file_item(self, path: "AlistPath", item, *field):
        """更新或创建FileItem"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_file_item(self, item_id: "AlistPath"):
        """获取FileItem"""
        raise NotImplementedError

    @abc.abstractmethod
    def create_log(self, worker: "Worker"):
        """"""


class MongoHandle(HandleBase):
    def __init__(self, mongodb: "Database"):
        self._workers: "Collection" = mongodb.workers
        self._items: "Collection" = mongodb.items
        self._logs: "Collection" = mongodb.logs

    def create_log(self, worker: "Worker"):
        logger.info(f"create log {worker.id} {worker.status}")
        self._logs.insert_one(worker.model_dump(mode="json"))

    def update_worker(self, worker: "Worker", *field):
        if field == ():
            data = worker.model_dump(mode="json")
        else:
            data = {k: worker.__dict__.get(k) for k in field}

        logger.debug(f"Worker[{worker.id}]: Update: {data}")
        return self._workers.update_one(
            {"_id": worker.id},
            {"$set": data},
            True if field == () else False,
        )

    def delete_worker(self, worker_id: str):
        logger.debug("删除Worker: %s", worker_id)
        return self._workers.delete_one({"_id": worker_id})

    def get_worker(self, worker_id: str):
        logger.debug("获取Worker: %s", worker_id)
        return self._workers.find_one({"_id": worker_id})

    def get_workers(self, query=None) -> Iterable:
        logger.debug("查询未完成的Worker.")
        if query is None:
            query = {}
        return self._workers.find(query)

    def load_locker(self) -> set["AlistPath"]:
        logger.info("正在加载MongoDB中保存的锁。")
        return {
            AlistPath(p)
            for doc in self._workers.find(
                {},
                {"source_path": True, "target_path": True},
            )
            for p in doc.values()
            if not None
        }

    def path_in_workers(self, path: "AlistPath") -> bool:
        return bool(
            self._workers.find_one(
                {"$or": [{"source_path": str(path)}, {"target_path": str(path)}]},
                {"_id": True},
            )
        )

    def update_file_item(self, path: "AlistPath", item, *field):
        if field == ():
            data = item.model_dump(mode="json")
        else:
            data = {k: item.__getattr__(k) for k in field}

        logger.debug("更新FileItem: %s", data)
        return self._items.update_one(
            {"_id": path.as_uri()},
            {
                "$set": {
                    "_id": item.id,
                    "update_time": datetime.datetime.now(),
                    "item": data,
                },
            },
            True if field == () else False,
        )

    def get_file_item(self, item_id: AlistPath):
        return self._items.find_one({"_id": item_id.as_uri()})["item"]


class ShelveHandle(HandleBase):
    def __init__(self, save_dir: Path):
        self._workers = shelve.open(
            str(save_dir.joinpath("alist_cache_workers.shelve")), writeback=True
        )
        self._items = shelve.open(
            str(save_dir.joinpath("alist_cache_items.shelve")), writeback=True
        )
        self._logs = save_dir.joinpath(
            "alist-sync-files.log",
        ).open("a+")

    def __del__(self):
        self._workers.close()
        self._items.close()
        self._logs.close()

    def create_log(self, worker: "Worker"):
        logger.debug(f"create log for: {worker.id}")
        self._logs.write(worker.model_dump_json())

    def update_worker(self, worker: "Worker", *field):
        logger.debug(f"Shelve[{worker.id}] update to workers")
        self._workers[worker.id] = worker.model_dump(mode="json")
        self._workers.sync()

    def delete_worker(self, worker_id: str):
        logger.debug(f"Worker[{worker_id}] remove from workers")
        try:
            self._workers.pop(worker_id)
        except KeyError:
            pass

    def get_worker(self, worker_id: str):
        logger.debug(f"get Worker[{worker_id}] from workers")
        return self._workers.get(worker_id)

    def get_workers(self, query=None) -> Iterable["Worker"]:
        logger.debug(f"get Workers from workers")
        for _w in self._workers.values():
            yield _w

    def load_locker(self) -> set[AlistPath]:
        logger.debug("正在加载Shelve中保存的锁。")
        return {
            AlistPath(p)
            for _w in self._workers.values()
            for p in (_w.source_path, _w.target_path)
            if p is not None
        }

    def path_in_workers(self, path: AlistPath) -> bool:
        return path in self.load_locker()

    def update_file_item(self, path: AlistPath, item, *field):
        logger.debug(f"FileItem[{path}] update to items")
        self._items[path.as_uri()] = {
            "id": path,
            "update_time": datetime.datetime.now(),
            "item": item,
        }

    def get_file_item(self, item_id: AlistPath):
        logger.debug(f"get FileItem[{item_id}] from items")
        return self._items.get(item_id.as_uri(), {}).get("item")
