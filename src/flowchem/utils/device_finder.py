"""Autodiscover any supported devices connected to the PC."""

from pathlib import Path

import aioserial
import rich_click as click
from loguru import logger
from serial.tools import list_ports

from flowchem.devices.hamilton.ml600_finder import ml600_finder
from flowchem.devices.harvardapparatus.elite11_finder import elite11_finder
from flowchem.devices.huber.huber_finder import chiller_finder
from flowchem.devices.knauer.knauer_finder import knauer_finder
from flowchem.devices.mettlertoledo.icir_finder import icir_finder
from flowchem.devices.vacuubrand.cvc3000_finder import cvc3000_finder
from flowchem.devices.vapourtec.vapourtec_finder import r4_finder

SERIAL_DEVICE_INSPECTORS = (
    ml600_finder,
    elite11_finder,
    chiller_finder,
    r4_finder,
    cvc3000_finder,
)


def inspect_serial_ports() -> set[str]:
    """Search for known devices on local serial ports and generate config stubs."""
    port_available = [comport.device for comport in list_ports.comports()]
    logger.info(
        f"Found the following serial port(s) on the current device: {port_available}",
    )

    dev_found_config: set[str] = set()
    # Loop each serial port
    for serial_port in port_available:
        logger.info(f"Looking for known devices on {serial_port}...")
        # Check if the serial port is available (i.e. not already open)
        try:
            port = aioserial.Serial(serial_port)
            port.close()
        except OSError:
            logger.info(f"Skipping {serial_port} (cannot be opened: already in use?)")
            continue

        # For each port try all functions that can detect serial port devices
        for inspector in SERIAL_DEVICE_INSPECTORS:
            # a list of config is return by the inspector, if len(config) == 0 then it is falsy
            if config := inspector(serial_port):
                dev_found_config.update(config)
                break
        logger.info(f"No known device found on {serial_port}")

    return dev_found_config


def inspect_eth(source_ip: str) -> set[str]:
    """Search for known devices on ethernet and generate config stubs."""
    logger.info("Starting ethernet detection")
    dev_found_config: set[str] = set()

    # Find Knauer
    knauer_devices = knauer_finder(source_ip)
    dev_found_config.update(knauer_devices)

    # Find iCIR
    icir = icir_finder()
    dev_found_config.update(icir)

    return dev_found_config


@click.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file",
    show_default=True,
    default="flowchem_config.toml",
)
@click.option(
    "--overwrite",
    "-w",
    is_flag=True,
    help="Overwrite existing configuration file if present",
)
@click.option("--safe", "-s", is_flag=True, help="Run only safe modules.")
@click.option(
    "--assume-yes",
    "--yes",
    "-y",
    is_flag=True,
    help="Assume 'yes' as answer to all prompts and run non-interactively.",
)
@click.option(
    "--source-ip",
    help="Source IP for broadcast packets. (Relevant if multiple eth interface are available)",
    default="",
)
def main(output, overwrite, safe, assume_yes, source_ip):
    """Auto-find devices connected to the current PC."""
    # Validate output location
    if Path(output).exists() and not overwrite:
        logger.error(
            f"Output file `{output}` already existing! Use `--overwrite` to replace it.",
        )
        return

    # Ask confirmation for serial communication
    confirm = False
    if not safe and not assume_yes:
        logger.warning(
            "The autodiscover include modules that involve communication over serial ports.",
        )
        logger.warning("These modules are *not* guaranteed to be safe!")
        logger.warning(
            "Unsupported devices could be placed in an unsafe state as result of the discovery process!",
        )
        confirm = click.confirm("Do you want to include the search for serial devices?")

    # Search serial devices
    serial_config = (
        inspect_serial_ports() if not safe and (assume_yes or confirm) else set()
    )

    # Search ethernet devices
    eth_config = inspect_eth(source_ip)

    # Print results
    if not serial_config and not eth_config:
        logger.error(f"No device found! The output file `{output}` won't be created.")
        return
    logger.info(f"Found {len(serial_config) + len(eth_config)} devices!")

    # Print configuration
    configuration = "".join(serial_config) + "".join(eth_config)
    logger.info(
        f"The following configuration will be written to `{output}:\n{configuration}",
    )

    # Write to file
    with Path(output).open("w", encoding="utf-8") as f:
        f.write(configuration)
    logger.info(f"Configuration written to `{output}`!")


if __name__ == "__main__":
    main()
