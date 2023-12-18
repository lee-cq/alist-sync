from pathlib import Path, PurePosixPath

import pytest
from alist_sdk import Item

from alist_sync.job_remove import RemoveJob
from alist_sync.checker import Checker
from alist_sync.job_copy import CopyJob
from alist_sync.scanner import Scanner

SUP_DIR = Path(__file__).parent.joinpath("resource")


@pytest.mark.parametrize(
    "scanner",
    [
        Scanner.model_validate_json(SUP_DIR.joinpath("Scanner.json").read_text()),
        Scanner.model_validate_json(SUP_DIR.joinpath("Scanner-m.json").read_text()),
    ],
)
def test_check(scanner: Scanner):
    cols = [PurePosixPath(base_path) for base_path, i in scanner.items.items()]
    checker: Checker = Checker.checker(scanner)
    assert checker.matrix
    assert checker.cols == cols


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
