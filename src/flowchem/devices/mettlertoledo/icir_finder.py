"""Autodiscover iCIR opcua server locally."""

import asyncio
import sys
from textwrap import dedent

from loguru import logger

from flowchem.devices import IcIR

__all__ = ["icir_finder"]

Address = tuple[str, int]


async def is_iCIR_running_locally() -> bool:
    """Is iCIR available on the local machine (default URL)?."""
    ir = IcIR()
    try:
        await ir.opcua.connect()
    except asyncio.TimeoutError:
        return False

    return await ir.is_iCIR_connected()


async def generate_icir_config() -> str:
    """Generate config string if iCIR is available."""
    if await is_iCIR_running_locally():
        logger.debug("Local iCIR found!")
        return dedent(
            """
               [device.icir-local]
               type = "IcIR"
               template = ""  # Add template name with acquisition settings!
               \n\n""",
        )
    return ""


def icir_finder():
    """Attempt connection on local iCIR instance."""
    # This is a bug of asyncio on Windows :|
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        return [asyncio.run(generate_icir_config())]
    except OSError:
        return []


if __name__ == "__main__":
    print(icir_finder())
