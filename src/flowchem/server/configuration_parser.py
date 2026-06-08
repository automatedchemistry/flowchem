"""Parse a device config file."""

import inspect
import sys
import typing
from io import BytesIO
from pathlib import Path

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.list_known_device_type import autodiscover_device_classes

if sys.version_info >= (3, 11):
    # noinspection PyUnresolvedReferences
    import tomllib
else:
    import tomli as tomllib

from loguru import logger

from flowchem.devices.known_plugins import plugin_devices
from flowchem.utils.exceptions import InvalidConfigurationError

DEVICE_NAME_MAX_LENGTH = 42


def parse_toml(stream: typing.BinaryIO) -> dict:
    """Read the TOML configuration file and returns it as a dict.

    Extensive exception handling due to the error-prone human editing needed in the configuration file.
    """
    try:
        return tomllib.load(stream)
    except tomllib.TOMLDecodeError as parser_error:
        logger.exception(parser_error)
        msg = "Invalid syntax in configuration!"
        raise InvalidConfigurationError(msg) from parser_error


def parse_config(file_path: Path | BytesIO) -> dict:
    """Parse a config file and add a `filename` key to the resulting dict w/ its location."""
    # BytesIO used for testing without creating actual files
    if isinstance(file_path, BytesIO):
        config = parse_toml(file_path)
        config["filename"] = "BytesIO"
    elif isinstance(file_path, Path):
        # Use explicit checks instead of assert, which is stripped by the -O optimisation flag.
        if not file_path.exists():
            raise InvalidConfigurationError(
                f"Configuration file not found: '{file_path}'"
            )
        if not file_path.is_file():
            raise InvalidConfigurationError(
                f"Configuration path is not a file: '{file_path}'"
            )

        with file_path.open("rb") as stream:
            config = parse_toml(stream)
        config["filename"] = file_path.stem
    else:
        raise InvalidConfigurationError("Invalid configuration type.")

    return config


def instantiate_device_from_config(config: dict) -> list[FlowchemDevice]:
    """Instantiate all devices defined in the provided config dict."""
    # Use an explicit check instead of assert, which is stripped by the -O optimisation flag.
    if "device" not in config:
        raise InvalidConfigurationError(
            "The configuration file must include a [device.*] section."
        )

    # device_mapper is a dict mapping device type (str, as key) with the device class (obj, value).
    # e.g. device_mapper["Spinsolve"] = Spinsolve class
    device_mapper = autodiscover_device_classes()

    # Iterate on all devices, parse device-specific settings and instantiate the relevant objects
    return [
        parse_device(dev_settings, device_mapper)
        for dev_settings in config["device"].items()
    ]


def ensure_device_name_is_valid(device_name: str) -> None:
    """Device name validator.

    Uniqueness of names is ensured by their toml dict key nature,
    """
    if len(device_name) > DEVICE_NAME_MAX_LENGTH:
        # f"{name}._labthing._tcp.local." has to be shorter than 64 characters to be valid for mDNS
        msg = f"Device name '{device_name}' is too long: {len(device_name)} characters, max is {DEVICE_NAME_MAX_LENGTH}"
        raise InvalidConfigurationError(msg)
    if "." in device_name:
        # This is not strictly needed but avoids potential zeroconf problems
        msg = f"Invalid character '.' in device name '{device_name}'"
        raise InvalidConfigurationError(msg)


def parse_device(dev_settings: dict, device_object_mapper: dict) -> FlowchemDevice:
    """Parse device config and return a device object.

    The device type (i.e. domain) is searched in the known classes (and known plugins, even if uninstalled).
    The device is instantiated via its `from_config` method or `init` if from_config is missing.
    The device object is returned.

    Exception handling to provide more specific and diagnostic messages upon errors in the configuration file.
    """
    device_name, device_config = dev_settings
    ensure_device_name_is_valid(device_name)

    # Get device class
    try:
        obj_type = device_object_mapper[device_config["type"]]
        del device_config["type"]
    except KeyError as error:
        # If the device type specified is supported via a plugin we know of, alert user
        if device_config["type"] in plugin_devices:
            needed_plugin = plugin_devices[device_config["type"]]
            logger.exception(
                f"The device `{device_name}` of type `{device_config['type']}` needs a additional plugin"
                f"Install {needed_plugin} to add support for it!"
                f"e.g. `python -m pip install {needed_plugin}`",
            )
            msg = f"{needed_plugin} not installed."
            raise InvalidConfigurationError(msg) from error

        logger.exception(
            f"Device type `{device_config['type']}` unknown in 'device.{device_name}'!"
            f"[Known types: {device_object_mapper.keys()}]",
        )
        msg = f"Unknown device type `{device_config['type']}`."
        raise InvalidConfigurationError(msg) from error

    # If the object has a 'from_config' method, use that for instantiation, otherwise try straight with the constructor.
    try:
        if hasattr(obj_type, "from_config"):
            called = obj_type.from_config
            device = obj_type.from_config(**device_config, name=device_name)
        else:
            called = obj_type.__init__
            device = obj_type(**device_config, name=device_name)
    except TypeError as error:
        logger.error(f"Wrong settings for device '{device_name}'!")
        get_helpful_error_message(device_config, inspect.getfullargspec(called))
        msg = (
            f"Wrong configuration provided for device '{device_name}' of type {obj_type.__name__}!\n"
            f"Configuration: {device_config}\n"
            f"Accepted parameters: {inspect.getfullargspec(called).args}"
        )

        raise ConnectionError(msg) from error

    logger.debug(f"Created '{device.name}' instance: {device.__class__.__name__}")
    return device


def get_helpful_error_message(called_with: dict, arg_spec: inspect.FullArgSpec) -> None:
    """Give helpful debugging text on configuration errors."""
    # First check if we have provided an argument that is not supported.
    # Clearly no **kwargs should be defined in the signature otherwise all kwargs are ok
    if arg_spec.varkw is None:
        invalid_parameters = list(set(called_with.keys()).difference(arg_spec.args))
        if invalid_parameters:
            logger.error(
                f"The following parameters were not recognized: {invalid_parameters}",
            )

    # Then check if a mandatory arguments was not satisfied. [1 to skip cls/self, -n to remove args w/ default]
    num_default = 0 if arg_spec.defaults is None else len(arg_spec.defaults)
    mandatory_args = arg_spec.args[1:-num_default]
    missing_parameters = list(set(mandatory_args).difference(called_with.keys()))
    if missing_parameters:
        logger.error(
            f"The following mandatory parameters were missing in the configuration: {missing_parameters}",
        )
