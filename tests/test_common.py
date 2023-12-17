import pytest
import asyncio

from pydantic import BaseModel

from alist_sync import common


class Task(BaseModel):
    status: str = "init"


def test_hash():
    assert common.sha1_6("123456") == "7c4a8d"


def test_asyncio_all_task_name():
    async def _test():
        asyncio.create_task(asyncio.sleep(2), name="sleep2")
        assert "sleep2" in common.async_all_task_names()

    asyncio.run(_test())


@pytest.mark.parametrize(
    "tasks, status, desc",
    [
        pytest.param([Task(status="success")], True, "list-success"),
        pytest.param({"name": Task(status="success")}, True, "dict-success"),
        pytest.param([], True, "list-[]"),
        pytest.param(
            [Task(status="success"), Task(status="running")], False, "list-running",
        ),
        pytest.param([Task()], False, "list-[init]"),
    ],
)
def test_is_task_all_success(tasks, status, desc):
    assert common.is_task_all_success(tasks) == status, desc
