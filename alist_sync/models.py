# 用于定义模型
from pathlib import Path

from pydantic import BaseModel as _BaseModel

from alist_sync.config import create_config

config = create_config()


__all__ = [
    "BaseModel",
]


class BaseModel(_BaseModel):
    """基础模型"""

    @classmethod
    def from_json_file(cls, file: Path):
        """从文件中读取json"""
        if not file.exists():
            raise FileNotFoundError(f"找不到文件：{file}")
        return cls.model_validate_json(Path(file).read_text(encoding="utf-8"))

    @classmethod
    def from_cache(cls):
        class_name = cls.__name__
        file = config.cache_dir.joinpath(f"{class_name}.json")
        return cls.from_json_file(file)

    def save_to_cache(self):
        class_name = self.__class__.__name__
        file = config.cache_dir.joinpath(f"{class_name}.json")
        file.write_text(self.model_dump_json(indent=2), encoding="utf-8")
