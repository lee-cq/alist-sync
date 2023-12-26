import asyncio

import pytest

from alist_sync.alist_client import AlistClient
from alist_sync.checker import Checker

from alist_sync.job_copy import CopyTask, CopyJob
from alist_sync.job_remove import RemoveTask, RemoveJob
from alist_sync.scanner import Scanner
from test_check import SUP_DIR

from .common import setup_module as _sm, setup_function as _sf, DATA_DIR, DATA_DIR_DST


setup_module = _sm


def setup_function():
    _sf()
    AlistClient(
        base_url="http://localhost:5244",
        verify=False,
        username="admin",
        password="123456",
    )


def test_base_task():
    from alist_sync.jobs import TaskBase

    TaskBase(
        need_backup=False,
        backup_status="init",
        backup_dir="",
    )


@pytest.mark.parametrize("need_backup", [True, False])
def test_copy_task(need_backup):
    """"""
    DATA_DIR.fs_path.joinpath("a.txt").write_text("123")
    DATA_DIR_DST.fs_path.joinpath("a.txt").write_text("21")
    DATA_DIR_DST.fs_path.joinpath(".alist-sync-data/history").mkdir(
        parents=True, exist_ok=True
    )

    task = CopyTask(
        copy_name="a.txt",
        copy_source=DATA_DIR.mount_path,
        copy_target=DATA_DIR_DST.mount_path,
        backup_dir=DATA_DIR_DST.mount_path + "/.alist-sync-data/history",
        need_backup=need_backup,
    )

    async def start():
        while True:
            if await task.check_status():
                break

    asyncio.run(start())
    assert DATA_DIR_DST.fs_path.joinpath("a.txt").read_text() == "123"
    # if need_backup:
    #     assert DATA_DIR_DST.fs_path.joinpath(".alist-sync-data").is_dir()


@pytest.mark.parametrize(
    "scanner",
    [
        Scanner.model_validate_json(SUP_DIR.joinpath("Scanner.json").read_text()),
        Scanner.model_validate_json(SUP_DIR.joinpath("Scanner-m.json").read_text()),
    ],
)
def test_job_copy_1_1(scanner):
    checker: Checker = Checker.checker(scanner)
    keys = list(scanner.items.keys())
    source = keys[0]
    target = keys[1]
    source_files = [_.full_name for _ in scanner.items.get(source)]
    target_files = [_.full_name for _ in scanner.items.get(target)]
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
    "scanner",
    [
        Scanner.model_validate_json(SUP_DIR.joinpath("Scanner.json").read_text()),
        Scanner.model_validate_json(SUP_DIR.joinpath("Scanner-m.json").read_text()),
    ],
)
def test_job_delete_1_1(scanner):
    checker: Checker = Checker.checker(scanner)
    keys = list(scanner.items.keys())
    source = keys[1]
    target = keys[0]
    source_files = [_.full_name for _ in scanner.items.get(source)]
    target_files = [_.full_name for _ in scanner.items.get(target)]
    job = RemoveJob.from_checker(
        source=source,
        target=target,
        checker=checker,
    )
    assert job.tasks
    for task in job.tasks.values():
        assert task.full_path not in source_files
        assert task.full_path in target_files
