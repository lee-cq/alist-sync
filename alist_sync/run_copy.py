import asyncio
import logging
from pathlib import PurePosixPath

from alist_sdk import Item, Task

from .base_sync import SyncBase
from .models import AlistServer, SyncDir, CopyTask

logger = logging.getLogger("alist-sync.copy-to-target")


class CopyToTarget(SyncBase):

    def __init__(self, alist_info: AlistServer, source_path: str, targets_path: list[str]):
        self.mode = 'copy'
        self.source_path = source_path
        self.targets_path = targets_path

        super().__init__(alist_info, [source_path, *targets_path])

    async def async_run(self):
        """异步运行"""
        await super().async_run()

        # 创建复制列表
        if not self.sync_task.copy_tasks:
            await self.create_copy_list()
            self.save_to_cache()
        else:
            logger.info(f"一件从缓存中找到 %d 个 CopyTask",
                        len(self.sync_task.copy_tasks))

        # 复制文件
        asyncio.create_task(self.copy_files(), name="copy_files")

        await self.check_status()
        logger.info("复制完成。")

    def create_copy_task(self, source: SyncDir, target: SyncDir):
        """通过比对源与目标到差异，创建复制列表"""
        for item in source.items:
            item: Item
            copy_path = item.full_name.relative_to(source.base_path)
            name = copy_path.name
            if target.in_items(copy_path):
                # 目标存在，判断是否需要更新
                logger.debug("[%s -> %s] %s: 目标存在",
                             source.base_path, target.base_path, copy_path)
                continue

            task = CopyTask(
                copy_name=name,  # 需要复制到文件名
                copy_source=PurePosixPath(source.base_path).joinpath(
                    copy_path.parent),  # 需要复制的源文件夹
                copy_target=PurePosixPath(target.base_path).joinpath(
                    copy_path.parent),  # 需要复制到的目标文件夹
            )
            self.sync_task.copy_tasks[task.name] = task
            self.save_to_cache()
            logger.debug("[%s -> %s] %s: 已创建复制任务信息。",
                         source.base_path, target.base_path, copy_path)

    @property
    def scaned_source_dir(self) -> SyncDir:
        _s = self.sync_task.sync_dirs.get(self.source_path)
        if _s is None:
            raise  # TODO
        return _s

    @property
    def scaned_targets_dir(self) -> list[SyncDir]:
        _ts = [self.sync_task.sync_dirs.get(t) for t in self.targets_path]
        if _ts:
            return _ts
        raise  # TODO

    async def create_copy_list(self):

        for sync_target in self.scaned_targets_dir:
            sync_target: SyncDir
            self.create_copy_task(
                self.sync_task.sync_dirs.get(self.source_path),
                sync_target
            )
            logger.info(
                "[%s -> %s] 复制任务信息全部创建完成。",
                self.scaned_source_dir.base_path,
                sync_target.base_path
            )

    async def copy_files(self):
        """复制文件"""

        async def copy(task, *args, **kwargs):
            res = await self.client.copy(*args, **kwargs)
            if res.code == 200:
                task.status = "created"
                self.save_to_cache()
                logger.info("[%s] 复制任务已经在AList中创建。", task.name)
            else:
                logger.warning("[%s] 复制任务创建失败。message: [%d]%s",
                               task.name, res.code, res.message)

        async def create_copy():
            while True:
                _need_create_copy = [
                    ct for ct in self.sync_task.copy_tasks.values() if ct.status == 'init'
                ]
                if not _need_create_copy:
                    logger.info("全部复制任务已经创建，create_copy exited.")
                    self.client.task_clear_done('copy')
                    break
                for copy_task in _need_create_copy:
                    copy_task: CopyTask
                    asyncio.create_task(
                        copy(
                            copy_task,
                            src_dir=copy_task.copy_source.as_posix(),
                            dst_dir=copy_task.copy_target.as_posix(),
                            files=[copy_task.copy_name, ]
                        ),
                        name=f"{id(self)}_copy_{copy_task.copy_name}"
                    )
                await asyncio.sleep(5)

        asyncio.create_task(create_copy())

    def status_wait(self, task: Task):
        """等待状态"""
        if self.sync_task.copy_tasks[task.name].status in ['created', ]:
            logger.debug("[%s] 在等待排队")
            self.sync_task.copy_tasks[task.name].status = 'waiting'

    def status_getting_src(self, task: Task):
        if self.sync_task.copy_tasks[task.name].status in ['created', 'waiting']:
            logger.debug("[%s] 正在下载源数据内容 %.2f %% ...", task.name, task.progress)
            self.sync_task.copy_tasks[task.name].status = 'getting_src'

    def status_failed(self, task: Task):
        logger.warning("[%s] 复制失败：error: %s", task.name, task.error)
        self.sync_task.copy_tasks[task.name].status = 'failed'

    def status_success(self, task: Task):
        logger.info("[%s] 复制完成。", task.name)
        self.sync_task.copy_tasks[task.name].status = 'success'

    def _not_de_status(self, task: Task):
        pass

    async def check_status(self):
        """状态更新"""

        status = {
            #
            "": self.status_wait,
            "getting src object": self.status_getting_src,
            "failed": self.status_failed,
            "success": self.status_success
        }
        while True:
            await asyncio.sleep(1)
            _, task_done = self.client.cached_copy_task_done

            _last_time, task_undone = self.client.cached_copy_task_undone
            _unsuccessful_task = [
                t for t in self.sync_task.copy_tasks.values() if t.status != "success"
            ]
            if not _unsuccessful_task:
                logger.info("全部的复制任务已经完成。")
                return
            if _last_time == 0:
                continue

            logger.info(f"等待复制完成, 剩余 %d ...", len(task_undone.data))

            for name, copy_task in _unsuccessful_task:
                copy_task: CopyTask
                ts = [
                    t for t in [*task_done, *task_undone] if t.name == copy_task.copy_name
                ]
                for t in ts:
                    if t.name not in self.sync_task.copy_tasks:
                        continue

                    ct: CopyTask = self.sync_task.copy_tasks.get(name)
                    if ct.id is None:
                        ct.id = t.id

                    try:
                        status[t.status](t)
                    except KeyError:
                        logger.error(f"Task Status 未定义： {t.status = }")
