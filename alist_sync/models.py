import datetime
from pathlib import PurePosixPath, Path
from typing import Optional

from pydantic import BaseModel, computed_field, Field
from alist_sdk import Item

from .alist_client import AlistClient

__all__ = ["AlistServer", "SyncDir", "CopyTask", "RemoveTask", "SyncTask"]


class AlistServer(BaseModel):
    """"""
    base_url: str = 'http://localhost:5244'
    username: Optional[str] = ''
    password: Optional[str] = ''
    token: Optional[str] = None
    has_opt: Optional[bool] = False

    # httpx 的参数
    verify: Optional[bool] = True
    headers: Optional[dict] = None


class SyncDir(BaseModel):
    """同步目录模型，定义一个同步目录"""
    base_path: str  # 同步基础目录
    items: list[Item]  # Item列表

    items_relative: Optional[list] = Field(exclude=True)  # Item列表相对路径

    def in_items(self, path) -> bool:
        """判断path是否在items中"""
        if not self.items_relative:
            self.items_relative = [i.full_name.relative_to(
                self.base_path) for i in self.items]
        return path in self.items_relative

    # @field_serializer('items_relative')
    # def serializer_items_relative(self, value, info) -> list:
    #     value: list[PurePosixPath] = []
    #     info: object
    #     return value


class CopyTask(BaseModel):
    """复制任务"""
    id: Optional[str] = None  # 创建任务后，Alist返回的任务ID  # 一个复制任务，对应对应了2个Alist任务
    copy_name: str  # 需要复制到文件名
    copy_source: PurePosixPath  # 需要复制的源文件夹
    copy_target: PurePosixPath  # 需要复制到的目标文件夹
    # 任务状态 init: 初始化，created: 已创建，"getting src object": 运行中，"": 已完成，"failed": 失败
    status: str = "init"
    message: Optional[str] = ''

    # @field_serializer('copy_source', 'copy_target')
    # def serializer_path(self, value: PurePosixPath, info):
    #     return value.as_posix()

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


class SyncDirs(BaseModel):
    source: Optional[SyncDir] = None
    targets: set[SyncDir] = {}

    @property
    def syncs(self) -> set[SyncDir]:
        if isinstance(self.source, SyncDir):
            return self.targets ^ {self.source, }
        return self.targets


class SyncTask(BaseModel):
    """同步任务"""
    alist_info: AlistServer  # Alist Info
    sync_dirs: SyncDirs  # 同步目录
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


if __name__ == '__main__':
    print(
        SyncTask(
            alist_info=AlistServer(),
            sync_dirs=[],
            copy_tasks={
                'aa': CopyTask(
                    copy_name='aa',
                    copy_source=PurePosixPath('/a'),
                    copy_target=PurePosixPath('/b/aa')
                )
            },
        ).model_dump_json(indent=2)
    )
