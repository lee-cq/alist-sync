#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : task.py
@Author     : LeeCQ
@Date-Time  : 2024/8/17 19:44
"""
import os
import threading
import time

from alist_sdk.models import Task
from alist_sdk.path_lib import ALIST_SERVER_INFO, AlistPath

from alist_sync.const import Env


class TaskStatus:
    """获取TaskStat"""

    def __init__(self):
        self.tasks: dict[str, Task] = dict()

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

    def thread_update_task(self):
        while not self.stop_event.is_set() or os.getenv(Env.exit_flag) == "true":
            time.sleep(2)
            self.update_task()

    def update_task(self):
        for c in ALIST_SERVER_INFO.values():
            done = c.task_done("copy")
            _cd = c.task_clear_succeeded("copy")
            if _cd.code != 200:
                f"清理失败, {c.base_url} - {_cd.message}"

            for i in done.data:
                self.tasks[i.id] = i

            undone = c.task_undone("copy")
            for i in undone.data:
                self.tasks[i.id] = i

    def get_task(self, _id) -> Task:
        return self.tasks.get(_id)

    def status(self, _id: str) -> str:
        try:
            return self.tasks[_id].status
        except KeyError:
            return "Unknown"


task_status = TaskStatus()

if __name__ == "__main__":
    from tools.func import get_server_info
    from alist_sdk.path_lib import login_server

    client = login_server(**get_server_info())
    print(client.task_done("copy"))
