"""Real drivers have to survive settings they don't know, e.g. `num_ports`, used only by flowchem-sim."""

import inspect

import aioserial
import pytest
import serial

import flowchem.devices.runze._common as runze_common
import flowchem.devices.vapourtec.ebpr as ebpr
import flowchem.devices.vapourtec.r2 as r2
import flowchem.devices.vapourtec.r4_heater as r4_heater
from flowchem.devices.hamilton.ml600 import ML600
from flowchem.devices.harvardapparatus.elite11 import Elite11
from flowchem.devices.knauer.knauer_autosampler import ASEthernetDevice, ASSerialDevice
from flowchem.devices.list_known_device_type import autodiscover_device_classes
from flowchem.devices.vicivalco.vici_valve import ViciValve
from flowchem.server.configuration_parser import parse_device
from flowchem.utils.serial_settings import SERIAL_SETTINGS, only_serial_settings

DEVICE_CLASSES = autodiscover_device_classes()

PYSERIAL_SETTINGS = {
    name
    for name, parameter in inspect.signature(
        serial.serialutil.SerialBase.__init__
    ).parameters.items()
    if name != "self" and parameter.kind is not parameter.VAR_KEYWORD
}

# Every device that forwards what is left of its configuration to the serial port.
SERIAL_DEVICES = {
    "CVC3000": {"port": "FAKE"},
    "EBPR": {"port": "FAKE"},
    "Elite11": {
        "port": "FAKE",
        "syringe_diameter": "14.567 mm",
        "syringe_volume": "10 ml",
    },
    "HeiConnect": {"port": "FAKE"},
    "HuberChiller": {"port": "FAKE"},
    "ML600": {"port": "FAKE", "syringe_volume": "5 ml"},
    "MansonPowerSupply": {"port": "FAKE"},
    "PeltierCooler": {"port": "FAKE", "address": 0},
    "R2": {"port": "FAKE"},
    "R4Heater": {"port": "FAKE"},
    "RunzeSyringePump": {"port": "FAKE", "syringe_volume": "5 mL"},
    "RunzeValve": {"port": "FAKE"},
    "SwitchBoxMPIKG": {"port": "FAKE"},
    "TMCM1110": {"port": "FAKE", "positions": {"a": 0}, "home_position": "a"},
    "TMCM1111": {"port": "FAKE", "positions": {"a": 0}, "home_position": "a"},
    "ViciValve": {"port": "FAKE", "address": 0},
}


@pytest.fixture
def opened_ports(monkeypatch):
    """Replace pyserial with a fake, and return the settings of each port "opened"."""
    opened: list[dict] = []

    class FakeSerial:
        """Opens nothing, and rejects unknown settings the way pyserial does."""

        def __init__(self, port=None, **settings):
            unknown = settings.keys() - PYSERIAL_SETTINGS
            if unknown:
                raise ValueError(f"unexpected keyword arguments: {unknown}")
            self.port = port or settings.get("port")
            opened.append(settings)

    monkeypatch.setattr(aioserial, "AioSerial", FakeSerial)
    monkeypatch.setattr(serial, "Serial", FakeSerial)

    # Connections are shared per port, so these would leak between test cases.
    monkeypatch.setattr(runze_common, "_shared_io_instances", {})
    for device_class in (ML600, Elite11, ViciValve):
        monkeypatch.setattr(device_class, "_io_instances", set())

    # The Vapourtec commands are under NDA, so they may be missing.
    for module, commands in (
        (ebpr, "VapourtecEBPRCommands"),
        (r2, "VapourtecR2Commands"),
        (r4_heater, "VapourtecR4Commands"),
    ):
        monkeypatch.setattr(module, "HAS_VAPOURTEC_COMMANDS", True)
        monkeypatch.setattr(module, commands, object, raising=False)

    return opened


def test_serial_settings_match_pyserial():
    assert SERIAL_SETTINGS == PYSERIAL_SETTINGS


def test_only_serial_settings_drops_the_rest_with_a_warning(logged_warnings):
    settings = {"port": "COM1", "baudrate": 9600, "num_ports": 6}

    assert only_serial_settings(settings) == {"port": "COM1", "baudrate": 9600}
    assert any("num_ports" in m for m in logged_warnings)


def test_only_serial_settings_is_silent_on_valid_settings(logged_warnings):
    assert only_serial_settings({"baudrate": 9600}) == {"baudrate": 9600}
    assert not logged_warnings


def test_real_pyserial_accepts_the_filtered_settings():
    """No port is given, so nothing gets opened."""
    settings = {"baudrate": 9600, "num_ports": 6}

    with pytest.raises(ValueError, match="num_ports"):
        serial.Serial(**settings)

    assert serial.Serial(**only_serial_settings(settings)).baudrate == 9600


@pytest.mark.parametrize(
    "device_type, settings", SERIAL_DEVICES.items(), ids=SERIAL_DEVICES
)
def test_serial_device_ignores_unknown_setting(
    device_type, settings, opened_ports, logged_warnings
):
    device = parse_device(
        ("dev", {"type": device_type, **settings, "num_ports": 6, "id": "UNIT-1"}),
        DEVICE_CLASSES,
    )

    assert device.name == "dev"
    assert device.device_info.id == "UNIT-1"
    assert "num_ports" not in opened_ports[0]
    assert any("num_ports" in m for m in logged_warnings)


@pytest.mark.parametrize(
    "device_type, settings", SERIAL_DEVICES.items(), ids=SERIAL_DEVICES
)
def test_serial_device_still_receives_serial_settings(
    device_type, settings, opened_ports, logged_warnings
):
    parse_device(
        ("dev", {"type": device_type, **settings, "baudrate": 1234}), DEVICE_CLASSES
    )

    assert opened_ports[0]["baudrate"] == 1234
    assert not any("unrecognized" in m for m in logged_warnings)


def test_devices_sharing_a_port_all_tolerate_the_unknown_setting(opened_ports):
    for name in ("valve1", "valve2"):
        settings = {"type": "RunzeValve", "port": "FAKE", "num_ports": 12}
        assert parse_device((name, settings), DEVICE_CLASSES).name == name

    assert len(opened_ports) == 1


@pytest.mark.parametrize("device_type", ["AzuraCompact", "KnauerValve"])
def test_knauer_device_ignores_unknown_setting(device_type, logged_warnings):
    """These forward their **kwargs up to FlowchemDevice, and connect only in initialize()."""
    device = parse_device(
        ("dev", {"type": device_type, "ip_address": "127.0.0.1", "num_ports": 6}),
        DEVICE_CLASSES,
    )

    assert device.name == "dev"
    assert any("dev" in m and "num_ports" in m for m in logged_warnings)


def test_autosampler_over_ethernet_ignores_unknown_setting(logged_warnings):
    io = ASEthernetDevice("127.0.0.1", tcp_port=1234, baudrate=9600)

    assert io.port == 1234
    assert any("baudrate" in m for m in logged_warnings)


def test_autosampler_over_serial_ignores_unknown_setting(opened_ports):
    ASSerialDevice(port="FAKE", baudrate=1234, num_ports=6)

    assert opened_ports[0]["baudrate"] == 1234
    assert "num_ports" not in opened_ports[0]
