from alist_sdk.py312_pathlib import PurePosixPath
import fnmatch

import pytest


@pytest.mark.parametrize(
    "path, match, result",
    [
        ["a/b/c/d", "a/*/*/d", True],
        ["a/b/c/d", "a/*/*/e", False],
        ["a/test.txt", "a/*.txt", True],
        ["a/b/test.txt", "a/*.txt", True],
        ["a/b/c/test.txt", "*.txt", True],
        [
            "电子书整理/睡眠革命/睡眠革命【微信公众号：冒犯经典】.mobi/Demo118_0_Text001.bfstm",
            "电子书整理/*",
            True,
        ],
        [
            "电子书整理/睡眠革命/睡眠革命【微信公众号：冒犯经典】.mobi/Demo118_0_Text001.bfstm",
            "*微信公众号：冒犯经典*",
            True,
        ],
    ],
)
def test_check(path, match, result):
    assert fnmatch.fnmatchcase(path, match) == result
