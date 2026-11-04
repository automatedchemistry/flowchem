from copy import deepcopy
from io import BytesIO
from textwrap import dedent

import pytest
from fastapi.testclient import TestClient
from flowchem.devices.fakedevice import FakeDevice

from flowchem.server.configuration_parser import (
    parse_config,
    ensure_device_name_is_valid,
    instantiate_device_from_config,
)
from flowchem.server.fastapi_server import FastAPIServer
from flowchem.utils.exceptions import InvalidConfigurationError


def _config(toml: str) -> dict:
    return parse_config(BytesIO(dedent(toml).encode("utf-8")))


def test_minimal_valid_config():
    cfg_txt = BytesIO(
        dedent(
            """
            [device.test-device]
            type = "FakeDevice"
            """,
        ).encode("utf-8"),
    )
    cfg = parse_config(cfg_txt)
    assert "filename" in cfg
    assert "device" in cfg


def test_device_instantiation():
    cfg_txt = BytesIO(
        dedent(
            """
            [device.test-device]
            type = "FakeDevice"
            """,
        ).encode("utf-8"),
    )
    cfg = parse_config(cfg_txt)
    devices = instantiate_device_from_config(cfg)
    assert isinstance(devices.pop(), FakeDevice)


def test_device_name_too_long():
    with pytest.raises(InvalidConfigurationError) as excinfo:
        ensure_device_name_is_valid("this_name_is_too_long_and_should_be_shorter")
    assert "too long" in str(excinfo.value)


def test_device_name_with_dot():
    with pytest.raises(InvalidConfigurationError) as excinfo:
        ensure_device_name_is_valid("this.name")
    assert "Invalid character" in str(excinfo.value)


def test_unknown_setting_is_ignored_with_a_warning(logged_warnings):
    cfg = _config("""
        [device.test-device]
        type = "FakeDevice"
        num_ports = 6
        """)
    assert isinstance(instantiate_device_from_config(cfg).pop(), FakeDevice)
    assert any("test-device" in m and "num_ports" in m for m in logged_warnings)


def test_known_setting_still_reaches_the_device(logged_warnings):
    cfg = _config("""
        [device.test-device]
        type = "FakeDevice"
        another_attribute = "custom"
        """)
    device = instantiate_device_from_config(cfg).pop()
    assert device.another_attribute == "custom"
    assert not any("unrecognized" in m for m in logged_warnings)


def test_missing_mandatory_setting_still_fails():
    """ViciValve needs `address`, and fails on it before touching the serial port."""
    cfg = _config("""
        [device.test-device]
        type = "ViciValve"
        port = "COM_DOES_NOT_EXIST"
        """)
    with pytest.raises(ConnectionError, match="Wrong configuration"):
        instantiate_device_from_config(cfg)


def test_name_setting_does_not_replace_the_section_name(logged_warnings):
    cfg = _config("""
        [device.test-device]
        type = "FakeDevice"
        name = "another-name"
        """)
    assert instantiate_device_from_config(cfg).pop().name == "test-device"
    assert any("name" in m for m in logged_warnings)


@pytest.mark.parametrize(
    "toml_value, expected", [('"PUMP-042"', "PUMP-042"), ("42", "42")]
)
def test_id_is_stored_in_device_info(toml_value, expected, logged_warnings):
    cfg = _config(f"""
        [device.test-device]
        type = "FakeDevice"
        id = {toml_value}
        """)
    assert instantiate_device_from_config(cfg).pop().device_info.id == expected
    assert not any("unrecognized" in m for m in logged_warnings)


def test_id_is_optional():
    cfg = _config("""
        [device.test-device]
        type = "FakeDevice"
        """)
    assert instantiate_device_from_config(cfg).pop().device_info.id is None


def test_config_is_not_modified():
    """flowchem-sim serves these same dicts at /startup_config."""
    cfg = _config("""
        [device.test-device]
        type = "FakeDevice"
        id = "PUMP-042"
        num_ports = 6
        """)
    expected = deepcopy(cfg)
    instantiate_device_from_config(cfg)
    assert cfg == expected


def test_id_is_served_by_the_device_endpoint():
    cfg = _config("""
        [device.test-device]
        type = "FakeDevice"
        id = "PUMP-042"
        """)
    server = FastAPIServer()
    server.add_device(instantiate_device_from_config(cfg).pop())

    response = TestClient(server.app).get("/test-device/")

    assert response.status_code == 200
    assert response.json()["id"] == "PUMP-042"
