
from pathlib import Path, PurePosixPath
from typing import Literal, Optional
from pydantic import BaseModel, computed_field, Field

from alist_sdk import Item

from alist_sync.alist_client import AlistClient
from alist_sync.models import Checker

CopyStatusModify = Literal[
    "init", "created", "waiting",
    "getting src object", "", "running", "success"
]


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

    async def check_status(self, client: AlistClient, ):
        """异步运行类 - 检查该Task的状态

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


class CopyJob(BaseModel):
    """复制工作 - 从Checker中找出需要被复制的任务并创建"""

    # client: AlistClient = Field(exclude=True)
    # checker: Checker = Field(exclude=True)
    tasks: dict[str, CopyTask]

    def dump(self):
        pass

    @classmethod
    def load_from_file(file: Path):
        pass

    @classmethod
    def from_checker(source, target, checker: Checker, ):
        """从Checker中创建Task"""
        _tasks: dict[str, CopyTask] = {}
        for r_path, pp in checker.matrix.items():
            _s: Item | None = pp.get(source)
            _t: Item | None = pp.get(target)
            if _s is not None and _t is None:
                _task = CopyTask(
                    copy_name=_s.name,  # 需要复制到文件名
                    copy_source=PurePosixPath(source.base_path).joinpath(
                        copy_path.parent),  # 需要复制的源文件夹
                    copy_target=PurePosixPath(target.base_path).joinpath(
                        copy_path.parent),  # 需要复制到的目标文件夹
                )
