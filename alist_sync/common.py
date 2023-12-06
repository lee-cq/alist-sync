import asyncio
import hashlib

import logging
import selectors
import sys

logger = logging.getLogger("alist-sync.common")

__all__ = [
    "sha1", "sha1_6", "async_all_task_names", "is_task_all_success", "timeout_input"
]


def sha1(s):
    return hashlib.sha1(str(s).encode()).hexdigest()


def sha1_6(s):
    hs = sha1(s)[:6]
    logger.debug("sha1[:6]: %s -> %s", s, hs)
    return hs


def async_all_task_names() -> set:
    """获取全部的task的name"""
    return {t.get_name() for t in asyncio.all_tasks()}


def is_task_all_success(tasks: list | dict) -> bool:
    if not tasks:
        return True
    if isinstance(tasks, dict):
        tasks = tasks.values()
    return all(1 if i.status == 'success' else 0 for i in tasks)


def timeout_input(msg, default, timeout=3):
    sys.stdout.write(msg)
    sys.stdout.flush()
    sel = selectors.DefaultSelector()
    sel.register(sys.stdin, selectors.EVENT_READ)
    events = sel.select(timeout)
    if events:
        key, _ = events[0]
        return key.fileobj.readline().rstrip()
    else:
        sys.stdout.write('\n')
        return default


if __name__ == "__main__":
    from pydantic import BaseModel

    class Task(BaseModel):
        status: str = "init"
    print(is_task_all_success(
        [Task(status='success'), Task(status='running'),]
    ))
