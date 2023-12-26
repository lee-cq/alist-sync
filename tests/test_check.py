from pathlib import Path, PurePosixPath

import pytest

from alist_sync.checker import Checker
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
