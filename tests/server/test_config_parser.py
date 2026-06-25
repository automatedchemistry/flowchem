from io import BytesIO
from textwrap import dedent

import pytest
from flowchem.devices.fakedevice import FakeDevice

from flowchem.server.configuration_parser import (
    parse_config,
    ensure_device_name_is_valid,
    instantiate_device_from_config,
)
from flowchem.utils.exceptions import InvalidConfigurationError


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
