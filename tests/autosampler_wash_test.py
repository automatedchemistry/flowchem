"""
Manual hardware test for the Knauer Autosampler wash routines.
==============================================================

Builds the platform-level ``Autosampler`` meta-component exactly the way the
real platform does (``experiment_sugar_activation_test.py`` /
``kinetic_campaign_activation.py``), then exercises two routines:

    1. ``fill_wash_reservoir()``
    2. ``wash_needle()``

This is a *manual* hardware test, NOT a pytest unit test: it moves the real
needle/syringe and needs the live flowchem device server plus the physical AS.
All heavy imports happen inside ``main()`` so pytest can import this file
during collection without side effects (there are no ``test_*`` functions, so
nothing is collected/run automatically).

Prerequisites
-------------
* The flowchem device server is running (``flowchem .\\devices.toml``) and the
  Autosampler ("AS") + external syringe ("external_pump") devices came up.
* This is the place where the connect-retry / teardown fix in
  ``flowchem/src/flowchem/devices/knauer/knauer_autosampler.py`` gets exercised
  for real: lots of short-lived AS commands == lots of connect/close cycles.

Run (from the flow_platform virtual environment)::

    python autosampler_wash_test.py

Optionally point at a specific server instead of mDNS discovery::

    python autosampler_wash_test.py --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _add_platforms_to_path() -> Path:
    """Put the ``platforms`` package (in ``flowchem_last_version``) on sys.path.

    Layout:  MG_flow_platform/flowchem/tests/<this file>
             MG_flow_platform/flowchem_last_version/platforms/...
    """
    platforms_root = Path(__file__).resolve().parents[2] / "flowchem_last_version"
    if str(platforms_root) not in sys.path:
        sys.path.insert(0, str(platforms_root))
    return platforms_root


def _discover_devices(url: str | None):
    """Return the {device_name: FlowchemDeviceClient} dict from the server."""
    if url:
        from flowchem.client.client import get_flowchem_devices_from_url

        return get_flowchem_devices_from_url(url)
    # Same discovery the platform uses (zeroconf/mDNS).
    from flowchem.client.client import get_all_flowchem_devices

    return get_all_flowchem_devices()


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual AS wash-routine hardware test.")
    parser.add_argument(
        "--url",
        default=None,
        help="Flowchem server base URL (e.g. http://localhost:8000). "
        "If omitted, devices are discovered via mDNS like the platform does.",
    )
    parser.add_argument("--volume", default="0.2 ml", help="Wash volume (default: 0.2 ml).")
    parser.add_argument("--flow-rate", default="1 ml/min", help="Flow rate (default: 1 ml/min).")
    parser.add_argument("--times", type=int, default=1, help="wash_needle repetitions (default: 1).")
    args = parser.parse_args()

    _add_platforms_to_path()

    from loguru import logger
    from flowchem import ureg
    from platforms.meta_components.autosampler import Autosampler

    volume = ureg(args.volume)
    flow_rate = ureg(args.flow_rate)

    logger.info("Discovering flowchem devices...")
    flowchem_devices = _discover_devices(args.url)
    logger.info(f"Found devices: {sorted(flowchem_devices)}")

    for required in ("AS", "external_pump"):
        if required not in flowchem_devices:
            logger.error(
                f"Device '{required}' not found on the server. Is the flowchem "
                f"server running with the AS + external syringe configured?"
            )
            return 1

    # Build the Autosampler meta-component exactly like the platform does.
    # NOTE: the constructor calls .initialize() itself -> this homes the needle,
    # parks the valves and initializes the (external) syringe. That IS the
    # "initialize it" step.
    logger.info("Initializing Autosampler (homes needle + valves + syringe)...")
    AS = Autosampler(
        gantry3d=flowchem_devices["AS"]["gantry3D"],
        pump=flowchem_devices["external_pump"]["pump"],  # external syringe as AS pump
        syringe_valve=flowchem_devices["AS"]["syringe_valve"],
        injection_valve=flowchem_devices["AS"]["injection_valve"],
    )
    logger.info("Autosampler initialized.")

    # 1) Fill the wash reservoir.
    logger.info(f"fill_wash_reservoir(volume={volume}, flow_rate={flow_rate}) ...")
    AS.fill_wash_reservoir(volume=volume, flow_rate=flow_rate)
    logger.info("fill_wash_reservoir done.")

    # 2) Wash the needle.
    logger.info(f"wash_needle(volume={volume}, times={args.times}, flow_rate={flow_rate}) ...")
    AS.wash_needle(volume=volume, times=args.times, flow_rate=flow_rate)
    logger.info("wash_needle done.")

    logger.info("Autosampler wash test completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
