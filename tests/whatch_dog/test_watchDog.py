import sys
from pathlib import Path
from xprocess import ProcessStarter
from flowchem.client.client import get_all_flowchem_devices
import pytest
import time

@pytest.fixture(scope="module")
def api_dev(xprocess):
    config_file = Path(__file__).parent.resolve() / "fakedevice.toml"
    main = Path(__file__).parent.resolve() / ".." / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        pattern = "Uvicorn running"
        timeout = 30
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    yield get_all_flowchem_devices()
    xprocess.getinfo("flowchem_instance").terminate()


def test_whatchdog(api_dev):
    dev = api_dev['fake-device']['FakeSpecificComponent2']
    dev.put("watch", params={"api": "fake_receive_data", "greater_than": 1})
    time.sleep(4)
    dev.put("stop-watch")