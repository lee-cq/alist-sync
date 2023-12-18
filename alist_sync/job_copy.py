import logging
from pathlib import PurePosixPath
from typing import Literal, Optional, Iterator

from pydantic import computed_field

from alist_sync.alist_client import AlistClient, get_status
from alist_sync.models import BaseModel
from alist_sync.checker import Checker
from alist_sync.common import get_alist_client
from alist_sync.jobs import JobBase

logger = logging.getLogger("alist-sync.job_copy")

CopyStatusModify = Literal[
    "init",
    "created",
    "waiting",
    "getting src object",
    "",
    "running",
    "success",
    "failed",
    "checked_done",
]


class CopyTask(BaseModel):
    """复制任务"""

    id: Optional[str] = None  # 创建任务后，Alist返回的任务ID  # 一个复制任务，对应对应了2个Alist任务
    copy_name: str  # 需要复制到文件名
    copy_source: PurePosixPath  # 需要复制的源文件夹
    copy_target: PurePosixPath  # 需要复制到的目标文件夹
    # 任务状态 init: 初始化，created: 已创建，"getting src object": 运行中，"": 已完成，"failed": 失败
    status: CopyStatusModify = "init"
    message: Optional[str] = ""

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
        _t = (
            ""
            if target_path.parent.as_posix() == "."
            else target_path.parent.as_posix()
        )

        return f"copy [{source_provider}](/{source_path}) to [{target_provider}](/{_t})"

    async def create(self, client: AlistClient = None):
        """创建复制任务"""
        client = client or get_alist_client()
        if self.status != "init":
            raise ValueError(f"任务状态错误: {self.status}")
        _res = await client.copy(
            files=[
                self.copy_name,
            ],
            src_dir=self.copy_source,
            dst_dir=self.copy_target,
        )
        if _res.code == 200:
            self.status = "created"

    async def recheck_done(self, client: AlistClient = None) -> bool:
        """检查任务复制到文件是否已经存在与目标位置"""
        client = client or get_alist_client()
        _res = await client.get_item_info(
            str(self.copy_target.joinpath(self.copy_name))
        )
        if _res.code == 200 and _res.data.name == self.copy_name:
            self.status = "checked_done"
            return True
        else:
            logger.error(f"复查任务失败: [{_res.code}]{_res.message}: {self.name}")
            self.status = "failed"
            return False

    async def check_status(self, client: AlistClient = None) -> bool:
        """异步运行类 - 检查该Task的状态

        在异步循环中反复检查

        1. 在alist中创建 复制任务             :: init    -> created
        2. 检查复制任务已经存在于 undone_list  :: created -> running
        3. 检查任务已经失败 (重试3次)          :: running -> failed
        4. 检查任务已经完成                   :: running -> success
        5. 复查任务是否已经完成               :: success -> checked_done
        """
        client = client or get_alist_client()

        if self.status == "init":
            logger.debug("创建任务: %s", self.name)
            return await self.create(client)
        elif self.status == "checked_done":
            return True
        elif self.status == "success":
            return await self.recheck_done(client)
        try:
            _status, _p = await get_status(self.name)
            self.status = _status
            return False
        except ValueError:
            logger.error("获取任务状态失败: %s", self.name)
            self.status = "failed"
            return False


class CopyJob(JobBase):
    """复制工作 - 从Checker中找出需要被复制的任务并创建"""

    # tasks: task_name -> task
    tasks: dict[str, CopyTask]
    done_tasks: dict[str, CopyTask] = {}

    @staticmethod
    def create_task(_s, _t, checker: Checker) -> Iterator[CopyTask]:
        """创建复制任务"""
        _s, _t = PurePosixPath(_s), PurePosixPath(_t)
        if _s not in checker.cols and _t not in checker.cols:
            raise ValueError(f"Source: {_s} or Target: {_t} not in Checker")
        for r_path, pp in checker.matrix.items():
            if pp.get(_s) is not None and pp.get(_t) is None:
                yield CopyTask(
                    copy_name=pp.get(_s).name,
                    copy_source=PurePosixPath(_s).joinpath(r_path.parent),
                    copy_target=PurePosixPath(_t).joinpath(r_path.parent),
                )
