#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : models.py.py
@Author     : LeeCQ
@Date-Time  : 2024/8/16 21:41
"""
from datetime import datetime

from peewee import Model, CharField, DateTimeField, IntegerField, BooleanField

from peewee import SqliteDatabase, IntegrityError

db = SqliteDatabase("./test.db")


class BaseModel(Model):
    class Meta:
        database = db

    def save(self, force_insert=None, only=None):
        if force_insert is not None:
            return super(BaseModel, self).save(force_insert, only)
        try:
            if only is not None:
                return super(BaseModel, self).save(force_insert=False, only=only)
            return super(BaseModel, self).save(force_insert=True, only=only)
        except IntegrityError as _e:
            return self.update()

    @classmethod
    def create_no_error(cls, **query):
        try:
            return cls.create(**query)
        except:
            return None


class Config(BaseModel):
    """配置项"""

    key: str = CharField(primary_key=True)
    value: str = CharField()

    def __repr__(self):
        return f"<models.Config: {self.key}>"


class File(BaseModel):
    """文件"""

    abs_path: str = CharField(primary_key=True)
    parent: str = CharField()

    mtime: datetime = DateTimeField()
    size: int = IntegerField()
    hash: str = CharField(default="")

    update_time: datetime = DateTimeField()
    update_owner: str = CharField()

    def __eq__(self, other) -> bool:
        if self.hash:
            return self.hash == other.hash
        return self.mtime == other.mtime and self.size == other.size

    def __repr__(self):
        return f"<models.File: {self.abs_path}>"

    def is_new(self):
        return not self.get_or_none(abs_path=self.abs_path)


class Doer(BaseModel):
    """本次执行的记录"""

    abs_path: str = CharField(unique=True)

    def __repr__(self):
        return f"<models.{self.__class__}: {self.abs_path}>"

    @classmethod
    def clear(cls):
        cls.delete()


class TransferLog(BaseModel):
    """传输记录"""

    log_id: str = CharField(unique=True)
    transfer_type: str = CharField()
    source_path: str = CharField()
    target_path: str = CharField()
    backed_up: bool = BooleanField()

    def __repr__(self):
        tar = (
            f"{self.target_path}"
            if self.transfer_type == "delete"
            else f"{self.source_path} -> {self.target_path}"
        )
        return f"<models.TransferLog: [{self.transfer_type}]{tar}>"


if __name__ == "__main__":
    db.create_tables([Config, File, Doer, TransferLog])

    Config(key="b", value="aa").save()
