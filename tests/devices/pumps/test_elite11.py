import sys
from pathlib import Path
from xprocess import ProcessStarter
from flowchem.client.client import get_all_flowchem_devices
import pytest
import time

# pytest tests/devices/pump/test_elite11.py -s


@pytest.fixture(scope="module")
def api_dev(xprocess):

    config_file = Path(__file__).parent.resolve() / "elite11.toml"
    main = Path(__file__).parent.resolve() / ".." / ".." / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        # Process startup ends with this text in stdout (timeout is long cause some GA runners are slow)
        pattern = "Uvicorn running"
        timeout = 30

        # execute flowchem with current venv
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    yield get_all_flowchem_devices()
    xprocess.getinfo("flowchem_instance").terminate()


@pytest.mark.HApump
def test_infuse(api_dev):
    pump = api_dev['test']['pump']
    assert pump.put("infuse", params={"rate": "1 ml/min", "volume": "2 ml"})
    time.sleep(5)
    assert pump.get("is-pumping")
    time.sleep(5)
    pump.put("stop")
    msg = ("Two commands were sent to the pump in order to infuse 2 ml of fluid at 1 ml/min. "
           "Is it observed by you? Does the device behave as expected, i.e., does it present "
           "some movement? (yes, no):")
    response = input(msg)
    assert response.lower() == 'yes', "The user indicated that device worked."

