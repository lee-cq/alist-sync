# coding: utf8
"""基础同步
[dir1, dir2, dir3]

各个Dir分别成为源目录，并Copy至其他目录

"""
from alist_sync.models import AlistServer
from alist_sync.run_copy import Copy


class Sync:
    def __init__(self, alist_info: AlistServer, dirs: list[str] = None):
        pass
