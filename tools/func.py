#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : func.py
@Author     : LeeCQ
@Date-Time  : 2024/8/17 19:52
"""
import os
import pathlib


def load_env():
    ROOT_PATH = pathlib.Path(__file__).parent.parent
    for line in ROOT_PATH.joinpath(".env").read_text().split("\n"):
        line = line.strip(" ").strip("\t")
        if line and line.startswith("#"):
            continue
        k, v = line.split("=", 1)
        os.environ[k] = v


load_env()


def get_server_info() -> dict:
    return dict(
        server=os.getenv("ALIST_HOST"),
        username=os.getenv("ALIST_USERNAME"),
        password=os.getenv("ALIST_PASSWORD"),
    )
