"""Entry-point module for the command line prefixes, called in case you use `python -m flowchem`.
Why does this file exist, and why `__main__`? For more info, read:
- https://www.python.org/dev/peps/pep-0338/
- https://docs.python.org/3/using/cmdline.html#cmdoption-m.
"""
import asyncio
import sys
from pathlib import Path

import rich_click as click
import uvicorn
from loguru import logger

from flowchem import __version__
from flowchem.server.core import Flowchem


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
    help="Server host. 0.0.0.0 is used to bind to all addresses, do not use for internet-exposed devices!",
)
@click.option("-d", "--debug", is_flag=True, help="Print debug info.")
@click.version_option()
@click.command()
def main(device_config_file, logfile, host, debug):
    """Flowchem main program.

    Parse device_config_file and starts a server exposing the devices via REST-ful API.

    Args:
    ----
        device_config_file: Flowchem configuration file specifying device connection settings (TOML)
        logfile: Output file for logs.
        host: IP on which the server will be listening. Loopback IP as default, use LAN IP to enable remote access.
        debug: Print debug info
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if not debug:
        # Set stderr to info
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    logger.info(f"Starting flowchem v. {__version__}!")
    if logfile:
        logger.add(Path(logfile), level="DEBUG")
    logger.debug(f"Starting server with configuration file: '{device_config_file}'")

    async def main_loop():
        """Main application loop, the event loop is shared between uvicorn and flowchem."""
        flowchem = Flowchem()
        await flowchem.setup(Path(device_config_file))

        config = uvicorn.Config(
            flowchem.http.app,
            host=host,
            port=flowchem.port,
            log_level="info",
            timeout_keep_alive=3600,
        )
        server = uvicorn.Server(config)
        logger.info("Click on http://127.0.0.1:8000 to access device server.")
        await server.serve()

    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
