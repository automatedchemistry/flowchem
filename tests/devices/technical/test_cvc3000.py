"""Test CVC3000, needs actual connection to the device."""
from pathlib import Path
from xprocess import ProcessStarter
from flowchem.client.client import get_all_flowchem_devices
import pytest
import sys


@pytest.fixture(scope="module")
def api_dev(xprocess):

    config_file = Path(__file__).parent.resolve() / "cvc3000.toml"
    main = Path(__file__).parent.resolve() / ".." / ".." / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        # Process startup ends with this text in stdout (timeout is long cause some GA runners are slow)
        pattern = "Uvicorn running"
        timeout = 30

        # execute flowchem with current venv
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    devices = get_all_flowchem_devices()
    yield devices["cvc-test"]
    xprocess.getinfo("flowchem_instance").terminate()

@pytest.mark.CVC3000
async def test_status_and_unit(api_dev):
    cvc = api_dev
    status = cvc["pressure-control"].get("status")
    status = status.json()
    assert not status["is_pump_on"]

    pressure = cvc["pressure-control"].get("pressure")
    pressure = pressure.json()
    assert type(pressure) is float

    cvc["pressure-control"].put("power-on")

    status = cvc["pressure-control"].get("status")
    status = status.json()
    assert status["is_pump_on"]

    cvc["pressure-control"].put("power-off")
