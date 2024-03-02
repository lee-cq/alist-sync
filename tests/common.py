import os
import time
from pathlib import Path
from typing import NamedTuple

from alist_sdk import Client

from alist_sync.config import create_config

cache_dir = create_config().cache_dir


class StorageInfo(NamedTuple):
    mount_path: str
    fs_path: Path


WORKDIR = Path(__file__).parent
WORKDIR.mkdir(exist_ok=True, parents=True)
DATA_DIR = StorageInfo("/local", WORKDIR / "alist/test_dir")
DATA_DIR_DST = StorageInfo("/local_dst", WORKDIR / "alist/test_dir_dst")
DATA_DIR_DST2 = StorageInfo("/local_dst2", WORKDIR / "alist/test_dir_dst2")


def create_storage_local(client_, mount_name, local_path: Path):
    local_storage = {
        "mount_path": f"{mount_name}",
        "order": 0,
        "driver": "Local",
        "cache_expiration": 0,
        "status": "work",
        "addition": '{"root_folder_path":"%s","thumbnail":false,'
        '"thumb_cache_folder":"","show_hidden":true,'
        '"mkdir_perm":"750"}' % local_path.absolute().as_posix(),
        "remark": "",
        "modified": "2023-11-20T15:00:31.608106706Z",
        "disabled": False,
        "enable_sign": False,
        "order_by": "name",
        "order_direction": "asc",
        "extract_folder": "front",
        "web_proxy": False,
        "webdav_policy": "native_proxy",
        "down_proxy_url": "",
    }
    if f"{mount_name}" not in [
        i["mount_path"]
        for i in client_.get("/api/admin/storage/list").json()["data"]["content"]
    ]:
        data = client_.post("/api/admin/storage/create", json=local_storage).json()

        assert data.get("code") == 200, data.get("message") + f", {mount_name = }"
    else:
        print("已经创建，跳过 ...")


def clear_dir(path: Path):
    if not path.exists():
        return
    for item in path.iterdir():
        if item.is_dir():
            clear_dir(item)
        else:
            item.unlink()
    path.rmdir()


def setup_module():
    print("setup_module")
    assert os.system(f"bash {WORKDIR}/init_alist.sh") == 0
    DATA_DIR.fs_path.mkdir(parents=True, exist_ok=True)
    DATA_DIR_DST.fs_path.mkdir(parents=True, exist_ok=True)
    DATA_DIR_DST2.fs_path.mkdir(parents=True, exist_ok=True)
    time.sleep(2)
    _client = Client(
        "http://localhost:5244",
        verify=False,
        username="admin",
        password="123456",
    )
    create_storage_local(_client, *DATA_DIR)
    create_storage_local(_client, *DATA_DIR_DST)
    create_storage_local(_client, *DATA_DIR_DST2)


def setup_function():
    print("setup_function")
    clear_dir(DATA_DIR.fs_path)
    DATA_DIR.fs_path.mkdir(parents=True, exist_ok=True)
    clear_dir(DATA_DIR_DST.fs_path)
    DATA_DIR_DST.fs_path.mkdir(parents=True, exist_ok=True)
    clear_dir(DATA_DIR_DST2.fs_path)
    DATA_DIR_DST2.fs_path.mkdir(parents=True, exist_ok=True)
    clear_dir(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    setup_module()
    setup_function()