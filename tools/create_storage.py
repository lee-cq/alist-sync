#!/bin/env python3
"""存储器

1. 从缓存读取
2. 从URL读取
3. 从文件读取
"""
import json
import os
from pathlib import Path

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

remote_client = None
if remote_url:
    remote_client = ExtraClient(
        base_url=remote_url,
        username=remote_username,
        password=remote_password,
        verify=False,
    )
