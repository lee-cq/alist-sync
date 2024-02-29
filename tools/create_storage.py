#!/bin/env python3
"""存储器

1. 从缓存读取
2. 从URL读取
3. 从文件读取
"""
import json
import os
from pathlib import Path

from alist_sdk import Storage
from alist_sdk.tools.client import ExtraClient

PROJECT_ROOT = Path(__file__).parent.parent.absolute()

alist_config = json.loads(PROJECT_ROOT.joinpath("alist/data/config.json").read_text())

alist_port = alist_config["scheme"]["http_port"]
admin_password = os.getenv("_ALIST_ADMIN_PASSWORD", "123456")

remote_url = os.getenv("_ALIST_BACKUP_URL")
remote_username = os.getenv("_ALIST_BACKUP_USERNAME")
remote_password = os.getenv("_ALIST_BACKUP_PASSWORD")

local_client = ExtraClient(
    base_url=f"http://localhost:{alist_port}",
    username="admin",
    password=admin_password,
)

# 如果--， 删除全部存储器
if os.getenv("_RELOAD_STORAGE"):
    for i in local_client.admin_storage_list().data.content:
        local_client.admin_storage_delete(i.id)

# 创建本地存储器
local_client.admin_storage_create(
    Storage.model_validate(
        {
            "mount_path": "/alist-sync",
            "order": 0,
            "driver": "Local",
            "cache_expiration": 0,
            "status": "work",
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


remote_client = None
if remote_url:
    local_client.import_config_from_other_client(
        base_url=remote_url,
        username=remote_username,
        password=remote_password,
        verify=False,
    )
    exit(0)
