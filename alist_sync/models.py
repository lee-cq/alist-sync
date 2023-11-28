from pathlib import PurePosixPath
from typing import Optional

from pydantic import BaseModel, computed_field, field_serializer
from alist_sdk import Item

__all__ = ["AlistServer", "SyncDir", "CopyTask", "SyncTask"]


class AlistServer(BaseModel):
    """"""
    base_url: str = 'http://localhost:5244'
    username: Optional[str] = ''
    password: Optional[str] = ''
    token: Optional[str] = None
    has_opt: Optional[bool] = False

    # httpx 的参数
    verify: Optional[bool] = True


class SyncDir(BaseModel):
    """同步目录模型，定义一个同步目录"""
    base_path: str  # 同步基础目录
    items: list[Item]  # Item列表
    items_relative: Optional[list] = []  # Item列表相对路径

    def in_items(self, path) -> bool:
        """判断path是否在items中"""
        if not self.items_relative:
            self.items_relative = [i.full_name.relative_to(self.base_path) for i in self.items]
        return path in self.items_relative

    @field_serializer('items_relative')
    def serializer_items_relative(self, value, info) -> list:
        return []


class CopyTask(BaseModel):
    """复制任务"""
    id: Optional[str] = None  # 创建任务后，Alist返回的任务ID  # 一个复制任务，对应对应了2个Alist任务
    copy_name: str  # 需要复制到文件名
    copy_source: PurePosixPath  # 需要复制的源文件夹
    copy_target: PurePosixPath  # 需要复制到的目标文件夹
    status: str = "init"  # 任务状态 init: 初始化，created: 已创建，"getting src object": 运行中，"": 已完成，"failed": 失败
    message: Optional[str] = ''

    @field_serializer('copy_source', 'copy_target')
    def serializer_path(self, value: PurePosixPath, info):
        return value.as_posix()

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


class SyncTask(BaseModel):
    """同步任务"""
    alist_info: AlistServer  # Alist Info
    sync_dirs: list[SyncDir]  # 同步目录
    copy_tasks: dict[str, CopyTask]  # 复制目录


if __name__ == '__main__':
    print(
        SyncTask(
            alist_info=AlistServer(),
            sync_dirs=[],
            copy_tasks={
                'aa': CopyTask(copy_name='aa', copy_source=PurePosixPath('/a'), copy_target=PurePosixPath('/b/aa'))},
        ).model_dump_json(indent=2)
    )
