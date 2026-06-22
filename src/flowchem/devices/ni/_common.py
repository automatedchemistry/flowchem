"""Shared helpers for National Instruments devices."""

from __future__ import annotations

import importlib
import re
from typing import Any

from flowchem.utils.exceptions import InvalidConfigurationError


def import_nidaqmx() -> tuple[Any, Any, Any]:
    """Import NI-DAQmx lazily and return package, System, and constants module."""
    try:
        nidaqmx = importlib.import_module("nidaqmx")
        system = importlib.import_module("nidaqmx.system").System
        constants = importlib.import_module("nidaqmx.constants")
    except ImportError as error:
        raise InvalidConfigurationError(
            "National Instruments support requires the optional NI dependency and NI-DAQmx driver. "
            'Install the Python package with `python -m pip install "flowchem[ni]"` '
            "or `python -m pip install nidaqmx`, then verify the device in NI MAX.",
        ) from error
    return nidaqmx, system, constants


def resolve_ni_device(
    system: Any,
    module: str | None,
    product_fragment: str | None = None,
    device_label: str = "NI device",
) -> Any:
    """Resolve one NI-DAQmx device by NI MAX name and optional product type fragment."""
    devices = list(system.local().devices)
    matching_devices = [
        device
        for device in devices
        if product_fragment is None
        or product_fragment in _normalized_product_type(device)
    ]

    if module is not None:
        try:
            selected = next(device for device in devices if device.name == module)
        except StopIteration as error:
            raise InvalidConfigurationError(
                f"NI module '{module}' was not found by NI-DAQmx. "
                "Check the NI MAX device name and hardware connection.",
            ) from error
        if (
            product_fragment is not None
            and product_fragment not in _normalized_product_type(selected)
        ):
            raise InvalidConfigurationError(
                f"NI module '{module}' is '{getattr(selected, 'product_type', 'unknown')}', "
                f"not a {device_label}.",
            )
        return selected

    if len(matching_devices) == 1:
        return matching_devices[0]
    if not matching_devices:
        raise InvalidConfigurationError(f"No {device_label} was found by NI-DAQmx.")
    module_names = ", ".join(device.name for device in matching_devices)
    raise InvalidConfigurationError(
        f"Multiple {device_label} devices were found ({module_names}); "
        "set the 'module' config value explicitly.",
    )


def physical_channel_names(collection: Any) -> list[str]:
    """Return physical channel names from the different collection shapes used by NI-DAQmx."""
    for attribute in ("channel_names", "names"):
        names = getattr(collection, attribute, None)
        if names is not None:
            return [str(name) for name in names]
    try:
        return [str(getattr(channel, "name", channel)) for channel in collection]
    except TypeError:
        return []


def line_sort_key(line_name: str) -> tuple[str, int, int]:
    """Sort physical lines by path prefix, port number, then line number."""
    match = re.search(r"(.*/)?port(\d+)/line(\d+)$", line_name)
    if not match:
        return line_name, -1, -1
    prefix = match.group(1) or ""
    return prefix, int(match.group(2)), int(match.group(3))


def channel_sort_key(channel_name: str) -> tuple[str, int]:
    """Sort analog physical channels by prefix and trailing channel number."""
    prefix, number = _split_trailing_number(channel_name)
    return prefix, number


def terminal_config_from_string(
    constants: Any, terminal_config: str | None
) -> Any | None:
    """Translate a user-friendly terminal config string to a NI-DAQmx enum value."""
    if terminal_config is None or terminal_config == "":
        return None
    try:
        return getattr(constants.TerminalConfiguration, terminal_config.upper())
    except AttributeError as error:
        valid = [
            name
            for name in dir(constants.TerminalConfiguration)
            if name.isupper() and not name.startswith("_")
        ]
        raise InvalidConfigurationError(
            f"Invalid NI terminal_config '{terminal_config}'. Valid values include: {valid}."
        ) from error


def _normalized_product_type(device: Any) -> str:
    return (
        str(getattr(device, "product_type", ""))
        .upper()
        .replace("-", "")
        .replace(" ", "")
    )


def _split_trailing_number(value: str) -> tuple[str, int]:
    match = re.search(r"^(.*?)(\d+)$", value)
    if match is None:
        return value, -1
    return match.group(1), int(match.group(2))
