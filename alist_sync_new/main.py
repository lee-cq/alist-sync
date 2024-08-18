#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : main.py
@Author     : LeeCQ
@Date-Time  : 2024/8/19 0:20
"""
from typing import Optional
from functools import cached_property

import peewee
from pydantic import BaseModel


class Database(BaseModel):
    type: str = "sqlite"  # mysql or SQLite
    path: Optional[str] = ".data.db"  # SQLite 默认数据库存储位置
    host: Optional[str] = "localhost"
    port: Optional[int] = 3306
    username: Optional[str] = "test"
    password: Optional[str] = "test"
    database: Optional[str] = "alist-sync"

    @cached_property
    def db(self):
        return peewee.Database()



class Config(BaseModel):
    version: str = "1"  #
