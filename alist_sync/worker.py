from typing import Literal, Any

from pydantic import BaseModel
from alist_sdk.path_lib import AlistPath

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
]


class Worker(BaseModel):
    type: WorkerType
    need_backup: bool
    source_path: AlistPath
    target_path: AlistPath
    backup_dir: AlistPath | None = None
    status: WorkerStatus

    def __del__(self):
        self.tmp_file.unlink(missing_ok=True)

    def __init__(self, **data: Any):
        super().__init__(**data)

        self.tmp_file = cache_dir.joinpath(f"download_tmp_{sha1(self.source_path)}")

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


