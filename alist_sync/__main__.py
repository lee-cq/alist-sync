#!/bin/env python3
# coding: utf8
import logging
from pathlib import Path

from typer import Typer, Option, echo, style

from alist_sync.base_sync import SyncBase
from alist_sync.models import AlistServer
from alist_sync.run_copy import Copy
from alist_sync.run_mirror import Mirror
from alist_sync.run_sync import Sync
from alist_sync.run_sync_incr import SyncIncr

app = Typer()

_base_url: str = Option(
    'http://localhost:5244',
    '--host', '-h',
    help="Base URL for Alist Host",

)

_username: str = Option(
    '',
    "--username", "-u",
    help="Alist Admin Username"
)

_password: str = Option(
    '', "--password", "-p",
    help="Alist Admin Password"
)

_token: str = Option(
    '', "--token", "-t",
    help="Alist Admin Token"
)

_verify: bool = Option(
    False, "--verify", "-v",
    # is_flag=True,
    help="Verify SSL Certificates"
)

_stores_config: str | None = Option(
    None, '-c', '--store-path',
    help="一个包含存储配置的JSON文件，可以是AList的备份文件"
)


@app.command(name='check')
def check(
        base_url: str = _base_url,
        username: str = _username,
        password: str = _password,
        token: str = _token,
        verify: bool = _verify,
        storage_config: str = _stores_config,
        target: list[str] = Option(..., "--target", "-t", help="Check Path"),
):
    """检查各个存储中的文件状态"""
    alist_info = AlistServer(
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        verify=verify,
        storage_config=Path(storage_config) if storage_config else None,
    )
    echo(
        f"Will Be Check '{target} "
        f"on {alist_info.base_url} [{alist_info.username}] \n"
        f"将会从 {alist_info.storage_config} 存储库获取存储库信息。"
    )
    c = SyncBase(alist_info=alist_info, sync_dirs=target)
    c.run()
    c.sync_job.checker.model_dump_table()


@app.command(name="copy")
def copy(
        base_url: str = _base_url,
        username: str = _username,
        password: str = _password,
        token: str = _token,
        verify: bool = _verify,
        storage_config: str = _stores_config,
        source: str = Option(..., "--source", "-s", help="Source Path"),
        target: list[str] = Option(..., "--target", "-t", help="Target Path"),
):
    """复制任务"""
    alist_info = AlistServer(
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        verify=verify,
        storage_config=storage_config,
    )
    echo(
        f"Will Be Copy '{source}' -> {target} "
        f"on {alist_info.base_url} [{alist_info.username}]"
        f"将会从 {alist_info.storage_config} 存储库获取存储库信息。"
    )
    return Copy(alist_info, source_path=source, targets_path=target).run()


@app.command('mirror')
def mirror(
        base_url: str = _base_url,
        username: str = _username,
        password: str = _password,
        token: str = _token,
        verify: bool = _verify,
        storage_config: str = _stores_config,

        source: str = Option(..., "--source", "-s", help="Source Path"),
        target: list[str] = Option(..., "--target", "-t", help="Target Path"),
):
    """镜像"""
    alist_info = AlistServer(
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        verify=verify,
        storage_config=storage_config,
    )
    echo(f"Will Be Mirror '{source}' -> {target} "
         f"on {alist_info.base_url} [{alist_info.username}]"
         )
    return Mirror(alist_info, source_path=source, targets_path=target).run()


@app.command()
def sync(
        base_url: str = _base_url,
        username: str = _username,
        password: str = _password,
        token: str = _token,
        verify: bool = _verify,
        storage_config: str = _stores_config,
        sync_group: list[str] = Option(..., "--sync", "-s", help="Sync Group"),
):
    """同步任务"""
    alist_info = AlistServer(
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        verify=verify,
        storage_config=storage_config,
    )
    echo(style("Hello Sync", fg="green", bg="black", bold=True))
    return Sync(alist_info, sync_group)


@app.command(name='sync-incr')
def sync_incr(
        config_dir: str = Option(..., "--name", "-n", help="在Alist上存储的配置目录"),
        cache_dir: str = Option(Path(), "--cache-dir", "-c", help="配置缓存目录"),
        base_url: str = _base_url,
        username: str = _username,
        password: str = _password,
        token: str = _token,
        verify: bool = _verify,
        storage_config: str = _stores_config,
        sync_group: list[str] = Option(..., "--sync", "-s", help="Sync Group"),

):
    """增量同步"""
    alist_info = AlistServer(
        base_url=base_url,
        username=username,
        password=password,
        token=token,
        verify=verify,
        storage_config=storage_config,
    )
    echo(f"增量同步：{sync_group}")
    return SyncIncr(
        alist_info,
        config_dir,
        cache_dir,
        sync_group
    ).run()


if __name__ == '__main__':
    from rich.logging import RichHandler
    logger = logging.getLogger('alist-sync')
    handler = RichHandler()
    handler.setLevel("DEBUG")
    logger.addHandler(handler)
    logger.setLevel("DEBUG")
    app()
