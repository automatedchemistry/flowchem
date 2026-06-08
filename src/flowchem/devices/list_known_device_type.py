"""Auto-discover the device classes present in the device sub-folders and in the installed plugins."""

import inspect
from importlib.metadata import entry_points
from typing import Any

from loguru import logger

import flowchem.devices
from flowchem.devices.flowchem_device import FlowchemDevice


def is_device_class(test_object):
    """Return true if the object is a subclass of FlowchemDevice."""
    if getattr(test_object, "__module__", None) is None:
        return None
    return (
        inspect.isclass(test_object)
        and issubclass(test_object, FlowchemDevice)
        and test_object.__name__ != "FlowchemDevice"
    )


def _autodiscover_devices_in_module(module) -> dict[str, Any]:
    """Given a module, autodiscover the device classes and return them as dict(name, object)."""
    device_classes = inspect.getmembers(module, is_device_class)
    logger.debug(f"Found {len(device_classes)} device type(s) in {module.__name__}")
    # Dict of device class names and their respective classes, i.e. {device_class_name: DeviceClass}.
    return {obj_class[0]: obj_class[1] for obj_class in device_classes}


def autodiscover_first_party() -> dict[str, Any]:
    """Get classes from `flowchem.devices` subpackages."""
    return _autodiscover_devices_in_module(flowchem.devices)


def autodiscover_third_party() -> dict[str, Any]:
    """Get classes from packages with a `flowchem.devices` entrypoint.

    A plugin structure can be used to add devices from an external package via setuptools entry points.
    See https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata
    """
    return {
        k: v
        for ep in entry_points(group="flowchem.devices")
        for (k, v) in _autodiscover_devices_in_module(ep.load()).items()
    }


def autodiscover_device_classes() -> dict[str, Any]:
    """Get all the device-controlling classes, either from `flowchem.devices` or third party packages.

    First-party devices take priority over third-party ones on name collision.
    A warning is logged when a collision is detected so the overriding is explicit.
    """
    first = autodiscover_first_party()
    third = autodiscover_third_party()

    # Warn on name collisions so silent overrides don't go unnoticed.
    collisions = set(first.keys()) & set(third.keys())
    for name in collisions:
        logger.warning(
            f"Device class name '{name}' exists in both first-party and a third-party plugin. "
            f"The first-party implementation ({first[name]}) will be used."
        )

    # First-party devices overwrite third-party ones.
    return third | first


if __name__ == "__main__":
    logger.debug(
        f"The following device types were found: {list(autodiscover_device_classes().keys())}",
    )
