"""Settings accepted when opening a serial port."""

from typing import Any

from loguru import logger

# Named parameters of pyserial's SerialBase.__init__. Spelled out because serial.Serial
# takes (*args, **kwargs) on Windows, so they cannot be read from its signature.
SERIAL_SETTINGS = frozenset(
    {
        "port",
        "baudrate",
        "bytesize",
        "parity",
        "stopbits",
        "timeout",
        "xonxoff",
        "rtscts",
        "write_timeout",
        "dsrdtr",
        "inter_byte_timeout",
        "exclusive",
    }
)


def only_serial_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Return `config` without the settings pyserial does not accept, warning about them.

    Devices forward whatever is left of their configuration to the serial port, and pyserial
    raises ValueError on anything it doesn't know, e.g. `num_ports`, used by simulated devices.
    """
    ignored = sorted(config.keys() - SERIAL_SETTINGS)
    if ignored:
        logger.warning(f"Ignoring unrecognized settings: {ignored}")
    return {key: value for key, value in config.items() if key in SERIAL_SETTINGS}
