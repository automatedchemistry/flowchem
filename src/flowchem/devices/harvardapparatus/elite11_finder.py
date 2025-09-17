"""This module is used to discover the serial address of any Elite11 connected to the PC."""
import asyncio
from textwrap import dedent

from loguru import logger

from flowchem.devices.harvardapparatus.elite11 import Elite11, HarvardApparatusPumpIO
from flowchem.utils.exceptions import InvalidConfigurationError


# noinspection PyProtectedMember
def elite11_finder(serial_port) -> set[str]:
    """Try to initialize an Elite11 on every available COM port. [Does not support daisy-chained Elite11!]."""
    logger.debug(f"Looking for Elite11 pumps on {serial_port}...")
    # Static counter for device type across different serial ports
    if "counter" not in elite11_finder.__dict__:
        elite11_finder.counter = 0  # type: ignore
    cfg: set[str] = set()

    try:
        link = HarvardApparatusPumpIO(port=serial_port)
    except InvalidConfigurationError:
        # This is necessary only on failure to release the port for the other inspector
        return cfg

    # Check for echo
    link._serial.write(b"\r\n")
    if link._serial.readline() != b"\n":
        # This is necessary only on failure to release the port for the other inspector
        link._serial.close()
        return cfg

    # Parse status prompt
    pump = link._serial.readline().decode("ascii")
    address = int(pump[0:2]) if pump[0:2].isdigit() else 0

    try:
        test_pump = Elite11(
            link,
            syringe_diameter="20 mm",
            syringe_volume="10 ml",
            address=address,
        )
        asyncio.run(test_pump.pump_info())
    except InvalidConfigurationError:
        # This is necessary only on failure to release the port for the other inspector
        link._serial.close()
        return cfg

    logger.info(f"Elite11 found on <{serial_port}>")

    # Local variable for enumeration
    elite11_finder.counter += 1  # type: ignore
    msg = f"[device.elite11-{elite11_finder.counter}]"  # type:ignore
    msg += dedent(
        f"""
                   type = "Elite11"
                   port = "{serial_port}"
                   address = {address}
                   syringe_diameter = "XXX mm" # Specify syringe diameter!
                   syringe_volume = "YYY ml" # Specify syringe volume!\n\n""",
    )
    logger.info(f"Close the serial port: <{serial_port}>")
    link._serial.close()
    cfg.add(msg)
    return cfg