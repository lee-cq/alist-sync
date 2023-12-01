import asyncio
import hashlib

import logging

logger = logging.getLogger("alist-sync.common")

__all__ = [
    "sha1", "sha1_6", "async_all_task_names",
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
