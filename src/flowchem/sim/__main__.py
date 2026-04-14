"""
flowchem-sim entry point.

Identical to `flowchem.__main__` except that before the server starts, the
autodiscovered device mapper is passed through ``build_sim_device_mapper``
so every real device class is transparently swapped for its simulation
counterpart.  The TOML file is used unchanged.

Usage
-----
    flowchem-sim experiment.toml
    flowchem-sim --debug experiment.toml
    flowchem-sim --host 127.0.0.1 experiment.toml
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import rich_click as click
import uvicorn
from loguru import logger

from flowchem import __version__
from flowchem.server.core import Flowchem
from flowchem.devices.list_known_device_type import autodiscover_device_classes
from flowchem.sim.registry import build_sim_device_mapper

# ---------------------------------------------------------------------------
# Patched instantiation helper
# ---------------------------------------------------------------------------


def _instantiate_with_sim_mapper(config: dict):
    """Like ``instantiate_device_from_config`` but uses the simulation mapper."""
    from flowchem.server.configuration_parser import parse_device

    if "device" not in config:
        from flowchem.utils.exceptions import InvalidConfigurationError

        raise InvalidConfigurationError(
            "The configuration file must include a [device.*] section."
        )

    real_mapper = autodiscover_device_classes()
    sim_mapper = build_sim_device_mapper(real_mapper)

    return [
        parse_device(dev_settings, sim_mapper)
        for dev_settings in config["device"].items()
    ]


# ---------------------------------------------------------------------------
# Patched Flowchem.setup that injects the sim mapper
# ---------------------------------------------------------------------------


class SimFlowchem(Flowchem):
    """Flowchem subclass that uses simulated devices."""

    async def setup(self, config):  # type: ignore[override]
        from flowchem.server.configuration_parser import parse_config as _parse_config

        self.config = _parse_config(config)
        self.http.configuration_dict = dict(self.config)  # shallow copy is fine
        self.devices = _instantiate_with_sim_mapper(self.config)

        logger.info("[SIM] Initializing simulated device connection(s)...")
        for dev in self.devices:
            await dev.initialize()
        logger.info("[SIM] Simulated device(s) connected")

        for device in self.devices:
            await self.mdns.add_device(name=device.name)
            self.http.add_device(device)
        logger.info("[SIM] Server component(s) loaded successfully!")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.argument("device_config_file", type=click.Path(), required=True)
@click.option(
    "-l",
    "--log",
    "logfile",
    type=click.Path(),
    default=None,
    help="Save logs to file.",
)
@click.option(
    "-h",
    "--host",
    "host",
    type=str,
    default="0.0.0.0",
    help="Server host. 0.0.0.0 binds to all addresses.",
)
@click.option("-d", "--debug", is_flag=True, help="Print debug info.")
@click.version_option()
@click.command()
def main(device_config_file, logfile, host, debug):
    """flowchem-sim — start FlowChem with simulated (no-hardware) devices.

    Reads the same TOML configuration file as `flowchem` but replaces every
    real device driver with its simulation counterpart.  No physical
    instruments need to be connected.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if not debug:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    logger.info(f"Starting flowchem-sim v. {__version__} (SIMULATION MODE)")
    if logfile:
        logger.add(Path(logfile), level="DEBUG")
    logger.debug(f"Config file: '{device_config_file}'")

    async def main_loop():
        flowchem = SimFlowchem()
        await flowchem.setup(Path(device_config_file))

        config = uvicorn.Config(
            flowchem.http.app,
            host=host,
            port=flowchem.port,
            log_level="info",
            timeout_keep_alive=3600,
        )
        server = uvicorn.Server(config)
        logger.info(
            f"[SIM] Click on http://127.0.0.1:{flowchem.port} to access simulated device server."
        )
        await server.serve()

    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
