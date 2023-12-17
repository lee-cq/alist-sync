import json
from pathlib import Path, PurePosixPath

import pytest

from alist_sync.job_remove import RemoveJob
from alist_sync.models import SyncDir
from alist_sync.checker import Checker
from alist_sync.job_copy import CopyJob

SUP_DIR = Path(__file__).parent.joinpath("resource")


@pytest.mark.parametrize(
    "scanned_dirs",
    [
        [SyncDir(**s) for s in json.load(SUP_DIR.joinpath("SyncDirs.json").open())],
        [SyncDir(**s) for s in json.load(SUP_DIR.joinpath("SyncDirs-m.json").open())],
    ],
)
def test_check(scanned_dirs):
    cols = [PurePosixPath(i.base_path) for i in scanned_dirs]
    checker: Checker = Checker.checker(*scanned_dirs)
    assert checker.matrix
    assert checker.cols == cols


@pytest.mark.parametrize(
    "scanned_dirs",
    [
        [SyncDir(**s) for s in json.load(SUP_DIR.joinpath("SyncDirs.json").open())],
        [SyncDir(**s) for s in json.load(SUP_DIR.joinpath("SyncDirs-m.json").open())],
    ],
)
def test_job_copy_1_1(scanned_dirs):
    checker = Checker.checker(*scanned_dirs)
    source = scanned_dirs[0].base_path
    target = scanned_dirs[1].base_path
    source_files = [i.full_name for i in scanned_dirs[0].items]
    target_files = [i.full_name for i in scanned_dirs[1].items]
    job = CopyJob.from_checker(
        source=source,
        target=target,
        checker=checker,
    )
    assert job.tasks
    for task in job.tasks.values():
        assert task.copy_source.joinpath(task.copy_name) in source_files
        assert task.copy_target.joinpath(task.copy_name) not in target_files


@pytest.mark.parametrize(
    "scanned_dirs",
    [
        [SyncDir(**s) for s in json.load(SUP_DIR.joinpath("SyncDirs.json").open())],
        [SyncDir(**s) for s in json.load(SUP_DIR.joinpath("SyncDirs-m.json").open())],
    ],
)
def test_job_delete_1_1(scanned_dirs):
    checker = Checker.checker(*scanned_dirs)
    source = scanned_dirs[1].base_path
    target = scanned_dirs[0].base_path
    source_files = [i.full_name for i in scanned_dirs[1].items]
    target_files = [i.full_name for i in scanned_dirs[0].items]
    job = RemoveJob.from_checker(
        source=source,
        target=target,
        checker=checker,
    )
    assert job.tasks
    for task in job.tasks.values():
        assert task.full_path not in source_files
        assert task.full_path in target_files
