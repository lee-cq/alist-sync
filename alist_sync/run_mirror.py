# coding: utf-8
"""镜像复制

source -> [target, ...]

1. Source 复制到 Target，若Target中没有，复制
2. 若Target已经存在，忽略。
3. 若Target有source无，删除。

"""
from run_copy import CopyToTarget


class Mirror(CopyToTarget):

    def __init__(self, alist_info,
                 source_dir: str = None,
                 target_path: list[str] = []
                 ):
        if len(target_path) != 1:
            raise AttributeError("使用Mirror时，targets必须唯一.")
        super().__init__(alist_info, mode='mirror', source_dir=source_dir, target_path=target_path)

    async def async_run(self):
        await super().async_run()
