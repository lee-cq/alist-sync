# coding: utf8
"""基础同步
[dir1, dir2, dir3]

各个Dir分别成为源目录，并Copy至其他目录

"""
from .base_sync import SyncBase
from .run_copy import CopyToTarget
from .models import AlistServer


class Sync:

    def __init__(self,
                 alist_info: AlistServer,
                 dirs: list[str] = []
                 ):
        for source in dirs:
            targets = dirs.copy()
            targets.remove(source)
            CopyToTarget(alist_info, mode='copy', source_dir=source, target_path=targets)
