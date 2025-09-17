"""Test CVC3000, needs actual connection to the device."""
import time
from pathlib import Path
from xprocess import ProcessStarter
from flowchem.client.client import get_all_flowchem_devices
import pytest
import sys


@pytest.fixture(scope="module")
def api_dev(xprocess):

    config_file = Path(__file__).parent.resolve() / "manson.toml"
    main = Path(__file__).parent.resolve() / ".." / ".." / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        # Process startup ends with this text in stdout (timeout is long cause some GA runners are slow)
        pattern = "Uvicorn running"
        timeout = 30

        # execute flowchem with current venv
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    devices = get_all_flowchem_devices()
    yield devices["manson-test"]
    xprocess.getinfo("flowchem_instance").terminate()

@pytest.mark.Manson
async def test_operation(api_dev):
    manson = api_dev
    status = manson["power-control"].put("power-on")
    status = status.json()
    assert status

    manson["power-control"].put("voltage", params={"voltage": "12 V"})

    time.sleep(2)

    v = manson["power-control"].get("voltage")
    v = v.json()
    assert abs(v - 12) < 0.3  # Tolerance

    manson["power-control"].put("power-off")