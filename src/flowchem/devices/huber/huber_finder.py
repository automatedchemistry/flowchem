"""This module is used to discover the serial address of any Huber chiller connected to the PC."""
import asyncio
from textwrap import dedent

from loguru import logger

from flowchem.devices.huber.chiller import HuberChiller
from flowchem.utils.exceptions import InvalidConfigurationError


# noinspection PyProtectedMember
def chiller_finder(serial_port) -> set[str]:
    """Try to initialize a Huber chiller on every available COM port."""
    logger.debug(f"Looking for Huber chillers on {serial_port}...")
    dev_config: set[str] = set()

    try:
        chill = HuberChiller.from_config(port=serial_port)
    except InvalidConfigurationError:
        return dev_config

    try:
        asyncio.run(chill.initialize())
    except InvalidConfigurationError:
        chill._serial.close()
        return dev_config

    logger.info(f"Chiller #{chill._device_sn} found on <{serial_port}>")
    dev_config.add(
        dedent(
            f"""
                [device.huber-{chill._device_sn}]
                type = "HuberChiller"
                port = "{serial_port}"\n""",
        ),
    )
    logger.info(f"Close the serial port: <{serial_port}>")
    chill._serial.close()
    return dev_config
