import logging
from pathlib import Path, PurePosixPath
from typing import Literal, Optional
from pydantic import BaseModel, computed_field

from alist_sync.alist_client import AlistClient, get_status
from alist_sync.checker import Checker
from alist_sync.common import get_alist_client
from alist_sync.config import cache_dir

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

    async def create(self, client: AlistClient = None):
        """创建复制任务"""
        client = client or get_alist_client()
        if self.status != 'init':
            raise ValueError(f"任务状态错误: {self.status}")
        _res = await client.copy(
            name=self.name,
            source=self.copy_source,
            target=self.copy_target,
        )
        if _res.code == 200:
            self.status = 'created'

    async def recheck_done(self, client: AlistClient = None) -> bool:
        """检查任务复制到文件是否已经存在与目标位置"""
        client = client or get_alist_client()
        _res = await client.get_item_info(str(self.copy_target.joinpath(self.copy_name)))
        if _res.code == 200 and _res.data.name == self.copy_name:
            self.status = 'checked_done'
            return True
        else:
            logger.error(f"复查任务失败: [{_res.code}]{_res.message}: {self.name}")
            self.status = 'failed'
            return False

    async def check_status(self, client: AlistClient = None):
        """异步运行类 - 检查该Task的状态

        在异步循环中反复检查

        1. 在alist中创建 复制任务             :: init    -> created
        2. 检查复制任务已经存在于 undone_list  :: created -> running
        3. 检查任务已经失败 (重试3次)          :: running -> failed
        4. 检查任务已经完成                   :: running -> success
        5. 复查任务是否已经完成               :: success -> checked_done
        """
        client = client or get_alist_client()

        if self.status == 'init':
            return self.create(client)
        elif self.status == 'checked_done':
            return True
        elif self.status == 'success':
            return await self.recheck_done(client)

        _status, _p = await get_status(self.name)
        self.status = _status
        return False


class CopyJob(BaseModel):
    """复制工作 - 从Checker中找出需要被复制的任务并创建"""
    # tasks: task_name -> task
    tasks: dict[str, CopyTask]
    done_tasks: dict[str, CopyTask] = {}

    @classmethod
    def from_json_file(cls, file: Path):
        return cls.model_validate_json(
            Path(file).read_text(encoding='utf-8')
        )

    @classmethod
    def from_cache(cls):
        file = cache_dir.joinpath('copy_job.json')
        return cls.from_json_file(file)

    def save_to_cache(self):
        file = cache_dir.joinpath('copy_job.json')
        file.write_text(self.model_dump_json(indent=2), encoding='utf-8')

    @classmethod
    def from_checker(cls, source, target, checker: Checker, ):
        """从Checker中创建Task"""
        _tasks = {}

        def _1_1(sp: PurePosixPath, tp: PurePosixPath):
            sp, tp = PurePosixPath(sp), PurePosixPath(tp)
            if sp not in checker.cols and tp not in checker.cols:
                raise ValueError(f"Source: {sp} or Target: {tp} not in Checker")
            for r_path, pp in checker.matrix.items():
                if pp.get(sp) is not None and pp.get(tp) is None:
                    __t = CopyTask(
                        copy_name=pp.get(sp).name,
                        copy_source=PurePosixPath(sp).joinpath(r_path.parent),
                        copy_target=PurePosixPath(tp).joinpath(r_path.parent),
                    )
                    _tasks[__t.name] = __t

        def _1_n(sp, tps):
            sp = PurePosixPath(sp)
            _tps = [PurePosixPath(tp) for tp in tps]
            [_1_1(sp, tp) for tp in _tps if sp != tp]

        def _n_n(sps, tps):
            [_1_n(sp, tps) for sp in sps]

        if isinstance(source, str | PurePosixPath) and isinstance(target, str | PurePosixPath):
            _1_1(source, target)
        elif isinstance(source, str | PurePosixPath) and isinstance(target, list | tuple):
            _1_n(source, target)
        elif isinstance(source, list | tuple) and isinstance(target, list | tuple):
            _n_n(source, target)
        else:
            raise ValueError(f"source: {source} or target: {target} not support")

        self = cls(tasks=_tasks)
        self.save_to_cache()
        return cls(tasks=_tasks)

    async def start(self, client: AlistClient = None):
        """开始复制任务"""
        client = client or get_alist_client()
        while self.tasks:
            for t_name in [k for k in self.tasks.keys()]:
                task = self.tasks[t_name]
                if await task.check_status(client=client):
                    self.done_tasks[task.name] = task
                    self.tasks.pop(task.name)
                    continue
            self.save_to_cache()
