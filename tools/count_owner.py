#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : count_owner.py
@Author     : LeeCQ
@Date-Time  : 2024/3/4 12:49

"""
import sys

from alist_sync.config import create_config

sync_config = create_config()

col = sync_config.mongodb.logs
datas = col.find(
    {"owner": sys.argv[1]},
)
datas = list(datas)
for d in datas:
    print(d["source_path"], d["file_size"])

print(sum(_d["file_size"] for _d in datas if _d["file_size"]))
