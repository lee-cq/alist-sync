#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : config.py.py
@Author     : LeeCQ
@Date-Time  : 2024/8/19 0:27
"""
import os
from pathlib import Path


def load_env():
    def __load_env(lines: str):
        for line in lines.split("\n"):
            line = line.strip().strip("\t")
            if line == "" or line.startswith("#") or line.startswith(";"):
                continue
            k, v = line.split("=", 1)
            os.environ[k] = v

        _code = Path(__file__).parent
        if _code.joinpath(".env").exists():
            __load_env(_code.joinpath(".env").read_text())

        _code_root = _code.parent
        if _code_root.joinpath(".env").exists():
            __load_env(_code_root.joinpath(".env").read_text())

        if Path().joinpath(".env").exists():
            __load_env(Path().joinpath(".env").read_text())
