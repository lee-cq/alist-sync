import datetime
import json
from pathlib import PurePosixPath, Path
from typing import  Optional, Literal

from pydantic import BaseModel, computed_field, Field
from alist_sdk import Item

from alist_sync.alist_client import AlistClient

__all__ = ["AlistServer", "SyncDir", "CopyTask", "RemoveTask", "SyncTask", "Checker"]

CopyStatusModify = Literal["init", "created", "waitting","getting src object", "", "running", "seccess"]


class AlistServer(BaseModel):
    """"""
    base_url: str = 'http://localhost:5244'
    username: Optional[str] = ''
    password: Optional[str] = ''
    token: Optional[str] = None
    has_opt: Optional[bool] = False

    max_connect: int = 30  # 最大同时连接数
    storage_config: Path = []

    # httpx 的参数
    verify: Optional[bool] = True
    headers: Optional[dict] = None

    def storages(self) -> list[dict]:
        """返回给定的 storage_config 中包含的storages"""

        def is_storage(_st):
            if not isinstance(_st, dict):
                return False
            if 'mount_path' in _st and 'driver' in _st:
                return True
            return False

        if not self.storage_config:
            return []
        if not self.storage_config.exists():
            raise FileNotFoundError(f"找不到文件：{self.storage_config}")

        _load_storages = json.load(self.storage_config.open())
        if isinstance(_load_storages, list):
            _load_storages = [_s for _s in _load_storages if is_storage()]
            if _load_storages:
                return _load_storages
            raise KeyError()

        if isinstance(_load_storages, dict):
            if 'storages' in _load_storages:
                _load_storages = [
                    _s for _s in _load_storages['storages'] if is_storage()]
                if _load_storages:
                    return _load_storages
                raise KeyError()
            if is_storage(_load_storages):
                return [_load_storages, ]
            raise KeyError("给定的")


class SyncDir(BaseModel):
    """同步目录模型，定义一个同步目录"""
    base_path: str  # 同步基础目录
    items: list[Item]  # Item列表

    items_relative: Optional[list] = Field([], exclude=True)  # Item列表相对路径

    def in_items(self, path) -> bool:
        """判断path是否在items中"""
        if not self.items_relative:
            self.items_relative = [i.full_name.relative_to(
                self.base_path) for i in self.items]
        return path in self.items_relative


class CopyTask(BaseModel):
    """复制任务"""
    id: Optional[str] = None  # 创建任务后，Alist返回的任务ID  # 一个复制任务，对应对应了2个Alist任务
    copy_name: str  # 需要复制到文件名
    copy_source: PurePosixPath  # 需要复制的源文件夹
    copy_target: PurePosixPath  # 需要复制到的目标文件夹
    # 任务状态 init: 初始化，created: 已创建，"getting src object": 运行中，"": 已完成，"failed": 失败
    status: CopyStatusModify = "init"
    message: Optional[str] = ''
    @computed_field()
    @property
    def name(self) -> str:
        """Alist 任务名称"""
        source_full_path = self.copy_source.joinpath(self.copy_name)
        source_provider = source_full_path.parents[-2]
        source_path = source_full_path.relative_to(source_provider)

        target_full_path = self.copy_target.joinpath(self.copy_name)
        target_provider = target_full_path.parents[-2]
        target_path = target_full_path.relative_to(target_provider)
        _t = '' if target_path.parent.as_posix() == '.' else target_path.parent.as_posix()

        return f"copy [{source_provider}](/{source_path}) to [{target_provider}](/{_t})"

    async def _run(self, client: AlistClient, ):
        """异步运行类 - 该类负责Copy Task 的全部生铭周期。

        在异步循环中反复检查

        1. 在alist中创建 复制任务             :: init -> created
        2. 检查复制任务已经存在于 undone_list :: created -> running
        3. 检查任务已经失败 (重试3次)         :: running -> failed
        4. 检查任务已经完成                   :: running -> success
        """
        if self.name in client.cached_copy_task_undone[-1]:
            self.status = 'created'
        if self.name in client.cached_copy_task_done[-1]:
            self.status = 'success'


class RemoveTask(BaseModel):
    """删除文件的任务"""
    full_path: PurePosixPath | str
    status: str = 'init'


class SyncTask(BaseModel):
    """同步任务"""
    alist_info: AlistServer  # Alist Info
    sync_dirs: dict[str, SyncDir] = {}  # 同步目录
    checker: Optional['Checker'] = None
    copy_tasks: dict[str, CopyTask] = {}  # 复制目录
    remove_tasks: dict[str, RemoveTask] = {}  # 删除目录


class Config(BaseModel):
    """配置"""
    name: str
    alist_info: AlistServer
    config_dir: PurePosixPath
    cache_dir: Path
    sync_group: list[str]

    update_time: datetime.datetime
    create_time: datetime.datetime


class Checker(BaseModel):
    mixmatrix: dict[PurePosixPath, dict[PurePosixPath, Item]]
    cols: list[PurePosixPath]

    @classmethod
    def checker(cls, *scanned_dirs):
        _result = {}
        for scanned_dir in scanned_dirs:
            for item in scanned_dir.items:
                r_path = item.full_name.relative_to(
                    scanned_dir.base_path
                )
                try:
                    _result[PurePosixPath(r_path)].setdefault(PurePosixPath(scanned_dir.base_path), item)
                except KeyError:
                    _result[PurePosixPath(r_path)] = {PurePosixPath(scanned_dir.base_path): item}
        return cls(mixmatrix=_result, cols=[PurePosixPath(t.base_path) for t in scanned_dirs])
    
    def model_dump_table(self):
        """"""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column('r_path', style="dim red", )
        for col in self.cols:
            table.add_column(str(col), justify="center", vertical='middle')

        for r_path, raw in self.mixmatrix.items():
            table.add_row(
                str(r_path),
                *["True" if raw.get(tt) else "False" for tt in self.cols]
            )
        console.print(table)
    


if __name__ == '__main__':
    import json
    from pathlib import Path

    checker = Checker.checker(*[SyncDir(**s) for s in json.load(
        Path(__file__).parent.parent.joinpath('tests/resource/SyncDirs.json').open())
                        ])
    checker.model_dump_table()