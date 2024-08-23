#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__.py
@Author     : LeeCQ
@Date-Time  : 2024/8/19 23:55
"""
import os
import typer

from alist_sync.const import Env
from alist_sync.main import copy as main_copy

app = typer.Typer()


@app.command()
def copy(
    config=typer.Option(".config.yaml", "-c", "--config"),
):
    """复制逻辑"""
    os.environ[Env.config] = config

    main_copy()


app()
