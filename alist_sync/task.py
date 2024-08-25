#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : task.py
@Author     : LeeCQ
@Date-Time  : 2024/8/17 19:44
"""
import logging
import os
import threading
import time

from alist_sdk.models import Task
from alist_sdk.path_lib import ALIST_SERVER_INFO, AlistPath

from alist_sync.const import Env

logger = logging.getLogger("alist-sync.task")


class TaskStatus:
    """获取TaskStat"""

    def __init__(self):
        self.tasks: dict[str, Task] = dict()
        self.done: set[str] = set()
        self.undone: set[str] = set()

        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self.thread_update_task,
            name="task-status-updater",
            daemon=True,
        )
        self.thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.close()

    def in_task(self, source: AlistPath, target: AlistPath) -> bool:
        """判断source, target 是否在现有的Task清单中"""

        def _to_posix(s: str):
            return s.strip("[").strip(")").replace("](", "")

        def to_s_t(_name: str) -> tuple[str, str]:
            _name = _name.replace("copy ", "")
            _s, _t = _name.split(" to ")
            return _to_posix(_s), _to_posix(_t)

        return (source.as_posix(), target.parent.as_posix()) in {
            to_s_t(name) for name in self.tasks
        }

    def close(self):
        self.stop_event.set()
        self.thread.join()

    def set_task(self, task: Task):
        self.tasks[task.id] = task

    def thread_update_task(self):
        while not self.stop_event.is_set() or os.getenv(Env.exit_flag) == "true":
            time.sleep(2)
            try:
                self.update_task()
            except Exception as e:
                logger.exception(f"更新Task失败, {e}")

    def update_task(self):
        _tasks = {}
        for c in ALIST_SERVER_INFO.values():
            undone = c.task_undone("copy")
            done = c.task_done("copy")
            if all(i.progress < 60 for i in done.data):
                _cd = c.task_clear_succeeded("copy")
                if _cd.code != 200:
                    logger.warning(f"清理失败, {c.base_url} - {_cd.message}")

            # 更新Task状态
            [self.set_task(i) for i in done.data]
            [self.set_task(i) for i in undone.data]
            # 定义新的undone 和 上一次的undone
            _last_undone = self.undone
            self.undone = {i.id for i in undone.data}
            # 计算可能已经完成的Task，但是被错误的清理
            for i in _last_undone - self.undone:
                if self.tasks[i].state == 1:
                    self.tasks[i].state = 2

        self.tasks.update(_tasks)
        # 从tasks中删除已完成的Task
        for i in self.done:
            if i in self.tasks:
                del self.tasks[i]

        logger.info(
            f"更新Task成功, 共有{len(_tasks)}/{len(self.tasks)}个Task: {self.tasks.keys()}"
        )

    def get_task(self, _id) -> Task:
        return self.tasks.get(
            _id,
            Task(
                id=_id,
                name="Unknown",
                state=0,
                status="",
                progress=0,
                error="",
            ),
        )

    def status(self, _id: str) -> str:
        try:
            return self.tasks[_id].status
        except KeyError:
            logger.warning(f"Task {_id} not found in tasks: {self.tasks.keys()}")
            return "Unknown"

    def get_state_by_id(self, _id: str) -> int:
        try:
            return self.tasks[_id].state
        except KeyError:
            logger.warning(f"Task {_id} not found in tasks: {self.tasks.keys()}")
            return -1

    def remove_task(self, _id: str):
        try:
            self.done.add(_id)
            del self.tasks[_id]
        except KeyError:
            logger.warning(f"Task {_id} not found in tasks")


copy_tasks = TaskStatus()

if __name__ == "__main__":
    from tools.func import get_server_info
    from alist_sdk.path_lib import login_server

    client = login_server(**get_server_info())
    print(client.task_done("copy"))
