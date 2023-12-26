# coding: utf8
"""增量同步JOB


"""
import time

from pydantic import computed_field

from jobs import JobBase


class JobSync(JobBase):
    sync_group: list
    status: str = "init"

    @computed_field()
    def update_time(self) -> int:
        return int(time.time())

    @computed_field()
    def job_id(self) -> str:
        return ""  # FIXME 修复
