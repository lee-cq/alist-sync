#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : models.py
@Author     : LeeCQ
@Date-Time  : 2024/9/12 22:21
"""
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, BigInteger, Column


class AlistServer(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    host: str  # 主机地址
    username: Optional[str]  # 主机用户名
    password: Optional[str]  # 主机密码
    token: Optional[str]  # token


class Config(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str  # 配置值
    desc: Optional[str]  # 配置描述


class Index(SQLModel, table=True):
    """快速索引"""

    id: Optional[int] = Field(primary_key=True)
    abs_path: str  # 绝对路径
    parent: str  # 父目录

    mtime: datetime  # 最近修改时间
    size: int = Field(sa_column=Column(BigInteger()))  # 文件大小
    hash: str | None = Field(default=None)  # 文件hash值

    update_time: datetime = Field(default_factory=datetime.now)  # 更新时间


class File(Index, table=True):
    """文件"""

    update_owner: str  # 更新人员


class Doer(SQLModel, table=True):
    """执行记录器"""

    abs_path: str = Field(primary_key=True)


class TransferLog(SQLModel, table=True):
    """文件传输记录"""

    id: int = Field(
        primary_key=True,
    )
    log_id: str = Field(unique=True)  # 日志id
    transfer_type: str  # 传输类型
    source_path: str  # 源路径
    target_path: str  # 目标路径
    file_name: Optional[str]  # 文件名
    file_size: int  # 文件大小
    mtime: datetime  # 最近修改时间
    backup_path: Optional[str]  # 备份路径
    status: str = Field(default="init")  # 状态
    message: Optional[str]  # 信息
    start_time: datetime = Field(default_factory=datetime.now)  # 开始时间
    end_time: Optional[datetime]  # 结束时间

    def __repr__(self):
        return f"<TransferLog(id={self.id}, log_id={self.log_id}, transfer_type={self.transfer_type}, source_path={self.source_path}, target_path={self.target_path}, file_name={self.file_name}, file_size={self.file_size}, mtime={self.mtime}, backup_path={self.backup_path}, status={self.status}>"
