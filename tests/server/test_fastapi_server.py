from flowchem.devices.flowchem_device import RepeatedTaskInfo
from flowchem.server.fastapi_server import FastAPIServer


async def _noop():
    return None


def test_add_background_tasks_accepts_single_repeated_task():
    server = FastAPIServer()

    server.add_background_tasks(RepeatedTaskInfo(seconds_every=5, task=_noop))

    assert len(server.app.router.on_startup) == 1


def test_add_background_tasks_accepts_multiple_repeated_tasks():
    server = FastAPIServer()
    tasks = (
        RepeatedTaskInfo(seconds_every=5, task=_noop),
        RepeatedTaskInfo(seconds_every=10, task=_noop),
    )

    server.add_background_tasks(tasks)

    assert len(server.app.router.on_startup) == 2
