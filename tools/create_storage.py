#!/bin/env python3
"""存储器

1. 从缓存读取
2. 从URL读取
3. 从文件读取
"""
import datetime
import json
import os
from pathlib import Path

from alist_sdk import Storage
from alist_sdk.tools.client import ExtraClient

PROJECT_ROOT = Path(__file__).parent.parent.absolute()

alist_config = json.loads(PROJECT_ROOT.joinpath("alist/data/config.json").read_text())

alist_port = alist_config["scheme"]["http_port"]
admin_password = os.getenv("_ALIST_ADMIN_PASSWORD", ) or "123456"

remote_url = os.getenv("_ALIST_BACKUP_URL")
remote_username = os.getenv("_ALIST_BACKUP_USERNAME")
remote_password = os.getenv("_ALIST_BACKUP_PASSWORD")

local_client = ExtraClient(
    base_url=f"http://localhost:{alist_port}",
    username="admin",
    password=admin_password,
)

print("local_client =", admin_password)
# 如果--， 删除全部存储器
print("_RELOAD_STORAGE =", os.getenv("_RELOAD_STORAGE"))
if os.getenv("_RELOAD_STORAGE") == "true":
    for i in local_client.admin_storage_list().data.content or []:
        local_client.admin_storage_delete(i.id)

# 创建本地存储器

PROJECT_ROOT.joinpath("alist/alist-sync").mkdir(exist_ok=True, parents=True)
res = local_client.admin_storage_create(
    Storage.model_validate(
        {
            "mount_path": "/alist-sync",
            "order": 0,
            "driver": "Local",
            "cache_expiration": 0,
            "status": "work",
            "modified": datetime.datetime.now(),
            "addition": json.dumps(
                {
                    "root_folder_path": str(PROJECT_ROOT.joinpath("alist/alist-sync")),
                    "thumbnail": False,
                    "thumb_cache_folder": "",
                    "show_hidden": True,
                    "mkdir_perm": "777",
                }
            ),
            "remark": "",
            "disabled": False,
            "enable_sign": False,
            "order_by": "name",
            "order_direction": "asc",
            "extract_folder": "",
            "web_proxy": False,
            "webdav_policy": "native_proxy",
            "down_proxy_url": "",
        }
    )
)
print(res)


if remote_url:
    local_client.import_config_from_other_client(
        base_url=remote_url,
        username=remote_username,
        password=remote_password,
        verify=False,
    )
    exit(0)

_bk_file = PROJECT_ROOT.joinpath("alist-backup-config.json")
if _bk_file.exists():
    local_client.import_configs(json.loads(_bk_file.read_text()))
