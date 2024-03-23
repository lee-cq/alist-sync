import asyncio
import builtins
import datetime
import hashlib
import logging
import re
import selectors
import sys
import threading
from pathlib import Path
from typing import Iterable


logger = logging.getLogger("alist-sync.common")

__all__ = [
    "get_alist_client",
    "sha1",
    "sha1_6",
    "async_all_task_names",
    "is_task_all_success",
    "timeout_input",
    "clear_path",
    "all_thread_name",
    "prefix_in_threads",
    "transfer_speed",
    "beautify_size",
    "B",
    "KB",
    "MB",
    "GB",
]

B = 1
KB = B * 1024
MB = KB * 1024
GB = MB * 1024


# noinspection PyUnresolvedReferences
def get_alist_client() -> "AlistClient":
    """获取AlistClient"""
    if not hasattr(builtins, "alist_client"):
        raise ValueError("AlistClient未初始化")
    return getattr(builtins, "alist_client", None)


def clear_path(path: Path):
    """清除缓存"""
    for i in path.iterdir():
        if i.is_file():
            i.unlink()
        elif i.is_dir():
            clear_path(i)
            i.rmdir()


def sha1(s) -> str:
    return hashlib.sha1(str(s).encode()).hexdigest()


def sha1_6(s):
    hs = sha1(s)[:6]
    logger.debug("sha1[:6]: %s -> %s", s, hs)
    return hs


def async_all_task_names() -> set:
    """获取全部的task的name"""
    return {t.get_name() for t in asyncio.all_tasks()}


def is_task_all_success(tasks: Iterable | dict) -> bool:
    if not tasks:
        return True
    if isinstance(tasks, dict):
        tasks = tasks.values()
    return all(1 if i.status == "success" else 0 for i in tasks)


def all_thread_name() -> set:
    """返回全部的线程名字"""
    return {t.name for t in threading.enumerate()}


def prefix_in_threads(prefix) -> bool:
    """在活动的线程，是否存指定的线程名前缀"""
    for name in all_thread_name():
        if prefix in name:
            return True
    return False


def timeout_input(msg, default, timeout=3):
    sys.stdout.write(msg)
    sys.stdout.flush()
    sel = selectors.DefaultSelector()
    sel.register(sys.stdin, selectors.EVENT_READ)
    events = sel.select(timeout)
    if events:
        key, _ = events[0]
        # noinspection PyUnresolvedReferences
        return key.fileobj.readline().rstrip()
    else:
        sys.stdout.write("\n")
        return default


def beautify_size(byte_size: float) -> str:
    if byte_size < 1024:
        return f"{byte_size:.2f}B"
    byte_size /= 1024
    if byte_size < 1024:
        return f"{byte_size:.2f}KB"
    byte_size /= 1024
    if byte_size < 1024:
        return f"{byte_size:.2f}MB"
    byte_size /= 1024
    return f"{byte_size:.2f}GB"


def data_size_to_bytes(data_size: str) -> int:
    """数据大小转换为字节"""
    data_size = data_size.strip()
    if data_size == "-1":
        return -1
    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
    }
    match = re.match(r"^(\d+(\.\d+)?)\s*([a-zA-Z]+)$", data_size)
    if not match:
        raise ValueError("Invalid data size format")
    # 提取数值和单位
    size_number = float(match.group(1))
    unit = match.group(2).upper()
    unit = unit if unit else "B"
    unit = unit if unit.endswith("B") else unit + "B"
    # 检查单位是否有效
    if unit not in units:
        raise ValueError(f"Invalid unit: {unit}")
    # 计算字节数并返回
    return int(size_number * units[unit])


def transfer_speed(size, start: datetime.datetime, end: datetime.datetime) -> str:
    """转换速度"""
    speed = (size * 2) / (end - start).seconds
    return beautify_size(speed) + "/s"


if __name__ == "__main__":
    from pydantic import BaseModel

    class Task(BaseModel):
        status: str = "init"

    print(
        is_task_all_success(
            [
                Task(status="success"),
                Task(status="running"),
            ]
        )
    )
