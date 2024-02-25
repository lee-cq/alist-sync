import atexit
import datetime
import logging
from pathlib import Path
from typing import Literal, Any

from pydantic import BaseModel, computed_field, Field
from pymongo.collection import Collection
from pymongo.database import Database
from alist_sdk.path_lib import AlistPathType

from alist_sync.config import cache_dir
from alist_sync.common import sha1

WorkerType = Literal["delete", "copy"]
WorkerStatus = Literal[
    "init",
    "deleted",
    "back-upping",
    "back-upped",
    "downloading",
    "uploading",
    "copied",
    "done",
]

logger = logging.getLogger("alist-sync.worker")


class Worker(BaseModel):
    owner: str
    created_at: datetime.datetime = datetime.datetime.now()
    type: WorkerType
    need_backup: bool
    backup_dir: AlistPathType | None = None

    source_path: AlistPathType
    target_path: AlistPathType | None = None
    status: WorkerStatus = "init"
    error_info: BaseException | None = None

    # 私有属性
    workers: "Workers | None" = Field(None, exclude=True)
    collection: Collection | None = Field(None, exclude=True)

    model_config = {
        "arbitrary_types_allowed": True,
        "excludes": {"workers", "collection", "tmp_file"},
    }

    @computed_field(return_type=str)
    @property
    def _id(self) -> str:
        return sha1(f"{self.type}{self.source_path}{self.created_at}")

    @property
    def tmp_file(self) -> Path:
        return cache_dir.joinpath(f"download_tmp_{sha1(self.source_path)}")

    def update(self, *field: Any):
        if self.status == "done" and self.workers is not None:
            return self.workers.del_worker(self._id)
        return self.update_mongo(*field)

    def update_mongo(self, *field):
        """"""

        if field == ():
            data = self.model_dump(mode="json")
        else:
            data = {k: self.__getattr__(k) for k in field}

        logger.debug("更新Worker: %s", data)
        return self.collection.update_one(
            {"_id": self._id},
            {"$set": data},
            True if field == () else False,
        )

    def __del__(self):
        self.tmp_file.unlink(missing_ok=True)

    def backup(self):
        """备份"""
        if self.backup_dir is None:
            raise ValueError("Need Backup, But no Dir.")
        backup_file = self.source_path if self.type == "delete" else self.target_path

    def downloader(self):
        """HTTP多线程下载"""

    def upload(self):
        """上传到alist"""

    def copy_type(self):
        """复制任务"""

    def delete_type(self):
        """删除任务"""

    def run(self):
        """启动Worker"""
        if self.need_backup:
            self.backup()

        if self.type == "copy":
            self.copy_type()
        elif self.type == "delete":
            self.delete_type()


class Workers(BaseModel):
    workers: list[Worker] = []
    mongodb: Database

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **data: Any):
        super().__init__(**data)

        atexit.register(self.__del__)

    def __del__(self):
        for i in cache_dir.iterdir():
            if i.name.startswith("download_tmp_"):
                i.unlink(missing_ok=True)

    def load_from_mongo(self):
        """从MongoDB加载Worker"""
        for i in self.mongodb.workers.find():
            self.workers.append(Worker(**i))

    def add_worker(self, worker: Worker):
        self.workers.append(worker)

    def del_worker(self, _id: str):
        """删除Worker"""
        pass

    def run(self):
        for worker in self.workers:
            worker.run()


if __name__ == "__main__":
    import os
    from pymongo import MongoClient
    from pymongo.server_api import ServerApi

    logging.basicConfig(level=logging.DEBUG)

    uri = os.environ["MONGODB_URI"]

    client = MongoClient(uri, server_api=ServerApi("1"))
    # w = Worker(
    #     owner="admin",
    #     type="delete",
    #     need_backup=True,
    #     backer_dir=AlistPath("http://localhost:5244/local/.history"),
    #     source_path="http://localhost:5244/local/test.txt",
    #     collection=client.get_default_database().get_collection("workers"),
    # )
    # print(w.update())

    ws = Workers(mongodb=client.get_default_database())
    ws.load_from_mongo()
    for w in ws.workers:
        print(w)
