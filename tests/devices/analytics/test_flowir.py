"""Test FlowIR, needs actual connection to the device :(."""
from pathlib import Path
from xprocess import ProcessStarter
from flowchem.client.client import get_all_flowchem_devices
import pytest
import time
import sys


@pytest.fixture(scope="module")
def api_dev(xprocess):

    config_file = Path(__file__).parent.resolve() / "flowir.toml"
    main = Path(__file__).parent.resolve() / ".." / ".." / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        # Process startup ends with this text in stdout (timeout is long cause some GA runners are slow)
        pattern = "Uvicorn running"
        timeout = 30

        # execute flowchem with current venv
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    devices = get_all_flowchem_devices()
    yield devices["icir-local"]
    xprocess.getinfo("flowchem_instance").terminate()


@pytest.mark.FlowIR
async def test_spectrum_acquisition(api_dev):
    spectrometer = api_dev
    spectrometer["ir-control"].put("start-experiment")

    # Wait for a spectrum
    spectrum = spectrometer["ir-control"].put("acquire-spectrum").json()
    while not spectrum["wavenumber"]:
        spectrum = spectrometer["ir-control"].put("acquire-spectrum").json()
        print("Waiting spectrum ...")
        time.sleep(1)

    spectra_count = spectrometer["ir-control"].get("spectrum-count")

    while spectrometer["ir-control"].get("spectrum-count") == spectra_count:
        time.sleep(1)

    info = spectrometer.device_info.additional_info
    assert "spectrometer" in info
    assert "spectrometer_SN" in info
    assert "probe_SN" in info
    assert "detector" in info

    spectrometer["ir-control"].put("stop")
