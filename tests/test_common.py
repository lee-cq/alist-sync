
import pytest
import asyncio

from alist_sync import common


def test_hash():
    assert common.sha1_6('123456') == '7c4a8d'


def test_asyncio_all_task_name():
    async def _test():
        asyncio.create_task(asyncio.sleep(2), name='sleep2')
        assert 'sleep2' in common.async_all_task_names()

    asyncio.run(_test())
