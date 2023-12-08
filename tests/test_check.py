import json
from pathlib import Path

import pytest

from alist_sync.models import SyncDir, CheckModel
from alist_sync.checker import Checker

SUP_DIR = Path(__file__).parent.joinpath('resource')


@pytest.mark.parametrize(
    "scanned_dirs",
    [[SyncDir(**s) for s in json.load(SUP_DIR.joinpath('SyncDirs.json').open())]]
)
def test_checker(scanned_dirs):
    checker = Checker(*scanned_dirs)
    assert checker.result

@pytest.mark.parametrize(
    "scanned_dirs",
    [[SyncDir(**s) for s in json.load(SUP_DIR.joinpath('SyncDirs.json').open())]]
)
def test_check(scanned_dirs):
    checker = CheckModel.checker(*scanned_dirs)
    assert checker.matrix