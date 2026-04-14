"""Test Spinsolve, needs actual connection with the device."""

import asyncio
import time
from pathlib import Path

import pytest

from flowchem.devices import Spinsolve

# Change to match your environment ;)
host = "BSMC-YMEF002121"


@pytest.fixture(scope="session")
def nmr():
    """Needs an actual Spinsolve instance running on the host."""
    return Spinsolve(host=host)


@pytest.mark.Spinsolve
def test_connection(nmr: Spinsolve):
    assert isinstance(nmr, Spinsolve)


@pytest.mark.Spinsolve
def test_solvent_property(nmr: Spinsolve):
    test_string = "test-solvent"
    nmr.solvent = test_string
    time.sleep(0.2)  # Ensures property is set.
    assert nmr.solvent == test_string


@pytest.mark.Spinsolve
def test_sample_property(nmr: Spinsolve):
    test_string = "sample_name"
    nmr.sample = test_string
    time.sleep(0.2)  # Ensures property is set.
    assert nmr.sample == test_string


@pytest.mark.Spinsolve
def test_user_data(nmr: Spinsolve):
    # Assignment is actually addition
    nmr.user_data = {"key1": "value1"}
    time.sleep(0.2)  # Ensures property is set.
    assert "key1" in nmr.user_data
    nmr.user_data = {"key2": "value2"}
    time.sleep(0.2)  # Ensures property is set.
    assert "key1" in nmr.user_data
    assert "key2" in nmr.user_data
    # Removal obtained by providing empty strings
    nmr.user_data = {"key1": "", "key2": ""}
    time.sleep(0.2)  # Ensures property is set.
    assert "key1" not in nmr.user_data
    assert "key2" not in nmr.user_data


@pytest.mark.Spinsolve
async def test_hw_request(nmr: Spinsolve):
    hw_tree = await nmr.hw_request()
    assert hw_tree.find(".//SpinsolveSoftware") is not None


@pytest.mark.Spinsolve
async def test_request_available_protocols(nmr: Spinsolve):
    protocols = await nmr.load_protocols()
    assert isinstance(protocols, dict)
    assert "1D PROTON" in protocols


@pytest.mark.Spinsolve
def test_request_validation(nmr: Spinsolve):
    # VALID
    valid_protocol = {
        "Number": "8",
        "AcquisitionTime": "3.2",
        "RepetitionTime": "2",
        "PulseAngle": "45",
    }
    check_protocol = nmr._validate_protocol_request("1D EXTENDED+", valid_protocol)
    assert check_protocol == valid_protocol

    # INVALID NAME
    check_protocol = nmr._validate_protocol_request(
        "NON EXISTING PROTOCOL",
        valid_protocol,
    )
    assert not check_protocol

    # PARTLY VALID OPTIONS
    partly_valid = {
        "Number": "7",
        "AcquisitionTime": "3.2",
        "RepetitionTime": "2",
        "PulseAngle": "145",
    }
    with pytest.warns(UserWarning, match="Invalid value"):
        check_protocol = nmr._validate_protocol_request("1D EXTENDED+", partly_valid)
    assert check_protocol == {"AcquisitionTime": "3.2", "RepetitionTime": "2"}

    # INVALID OPTIONS 1
    partly_valid = {
        "Number": "7",
        "AcquisitionTime": "43.2",
        "RepetitionTime": "2123092183",
        "PulseAngle": "145",
    }
    with pytest.warns(UserWarning, match="Invalid value"):
        check_protocol = nmr._validate_protocol_request("1D EXTENDED+", partly_valid)
    assert not check_protocol

    # INVALID OPTIONS 21
    partly_valid = {
        "Number": "8",
        "AcquisitionTime": "3.2",
        "RepetitionTime": "2",
        "PulseAngle": "45",
        "blabla": "no",
    }
    with pytest.warns(UserWarning, match="Invalid option"):
        check_protocol = nmr._validate_protocol_request("1D EXTENDED+", partly_valid)
    assert "blabla" not in check_protocol


@pytest.mark.Spinsolve
def test_data_folder(nmr: Spinsolve):
    nmr.data_folder = "C:/data/myfolder"
    time.sleep(0.1)
    assert nmr.data_folder == "C:/data/myfolder"
    nmr.data_folder = "C:/data/myfolder"
    time.sleep(0.1)
    assert nmr.data_folder == "C:/data/myfolder"
    nmr.data_folder = "C:/data/myfolder"
    time.sleep(0.1)
    assert nmr.data_folder == "C:/data/myfolder"


@pytest.mark.Spinsolve
def test_protocol(nmr: Spinsolve):
    # back to default
    nmr.data_folder = ""
    time.sleep(0.1)

    # Run fast proton
    path = asyncio.run(nmr.run_protocol("1D PROTON", options={"Scan": "QuickScan"}))
    assert isinstance(path, Path)


@pytest.mark.Spinsolve
def test_invalid_protocol(nmr: Spinsolve):
    # back to default
    nmr.data_folder = ""
    time.sleep(0.1)

    # Fail on plutonium
    with pytest.warns(UserWarning, match="not available"):
        path = asyncio.run(
            nmr.run_protocol("1D PLUTONIUM", options={"Scan": "QuickScan"})
        )
    assert path is None
