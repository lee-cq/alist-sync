from pathlib import Path


def create_storage_local(client_, mount_name, local_path: Path):
    local_storage = {
        "mount_path": f"/{mount_name}",
        "order": 0,
        "driver": "Local",
        "cache_expiration": 0,
        "status": "work",
        "addition": "{\"root_folder_path\":\"%s\",\"thumbnail\":false,"
                    "\"thumb_cache_folder\":\"\",\"show_hidden\":true,"
                    "\"mkdir_perm\":\"750\"}" % local_path.absolute().as_posix(),
        "remark": "",
        "modified": "2023-11-20T15:00:31.608106706Z",
        "disabled": False,
        "enable_sign": False,
        "order_by": "name",
        "order_direction": "asc",
        "extract_folder": "front",
        "web_proxy": False,
        "webdav_policy": "native_proxy",
        "down_proxy_url": ""
    }
    if f'/{mount_name}' not in [
        i['mount_path']
        for i in client_.get("/api/admin/storage/list").json()['data']['content']
    ]:
        data = client_.post(
            "/api/admin/storage/create",
            json=local_storage).json()
        
        assert data.get('code') == 200, data.get(
            "message") + f", {mount_name = }"
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
