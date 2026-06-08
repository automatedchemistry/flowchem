"""Control an NI-9477 digital output module through NI-DAQmx."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Sequence
from typing import Any

from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.ni.ni9477_component import NI9477Relay
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.utils.people import samuel_saraiva

NI9477_CHANNEL_COUNT = 32


class NI9477(FlowchemDevice):
    """NI-9477 32-channel sinking digital output module in a CompactDAQ chassis."""

    def __init__(
        self,
        module: str,
        task: Any,
        name: str = "",
        reset_outputs_on_initialize: bool = True,
        line_names: Sequence[str] | None = None,
        serial_number: str | int = "unknown",
    ) -> None:
        super().__init__(name)
        self.module = module
        self._task = task
        self.reset_outputs_on_initialize = reset_outputs_on_initialize
        self._line_names = (
            list(line_names) if line_names else self.default_line_names(module)
        )
        self._channel_states = [False] * NI9477_CHANNEL_COUNT
        self._write_lock = asyncio.Lock()

        if len(self._line_names) != NI9477_CHANNEL_COUNT:
            raise InvalidConfigurationError(
                f"NI9477 requires {NI9477_CHANNEL_COUNT} digital output lines, "
                f"got {len(self._line_names)} for module '{module}'.",
            )

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="National Instruments",
            model="NI-9477",
            serial_number=serial_number,
            additional_info={
                "module": module,
                "channels": NI9477_CHANNEL_COUNT,
                "output_type": "sinking digital output",
            },
        )

    @classmethod
    def from_config(
        cls,
        module: str | None = None,
        name: str = "",
        reset_outputs_on_initialize: bool = True,
    ) -> "NI9477":
        """Create an NI9477 from Flowchem TOML configuration."""
        nidaqmx, system, line_grouping = _import_nidaqmx()
        module_device = cls._resolve_module(system, module)
        module_name = module_device.name
        line_names = cls._discover_line_names(module_device, module_name)
        task = nidaqmx.Task()
        task.do_channels.add_do_chan(
            ",".join(line_names),
            line_grouping=line_grouping.CHAN_PER_LINE,
        )

        return cls(
            module=module_name,
            task=task,
            name=name,
            reset_outputs_on_initialize=reset_outputs_on_initialize,
            line_names=line_names,
            serial_number=getattr(module_device, "serial_num", "unknown"),
        )

    async def initialize(self) -> None:
        """Register the relay component and optionally set all outputs OFF."""
        if self.reset_outputs_on_initialize:
            initialized = await self.set_channels([False] * NI9477_CHANNEL_COUNT)
            if not initialized:
                raise InvalidConfigurationError(
                    "Could not reset NI9477 output channels during initialization."
                )

        self.components.append(NI9477Relay("relay", self))
        logger.info(
            f"Connected to NI-9477 module '{self.module}' with {NI9477_CHANNEL_COUNT} digital outputs."
        )

    async def set_channel(self, channel: str | int, active: bool) -> bool:
        """Set one output channel active or inactive."""
        channel_index = self._channel_index(channel)
        next_states = self._channel_states.copy()
        next_states[channel_index] = active
        return await self.set_channels(next_states)

    async def set_channels(self, states: Sequence[bool]) -> bool:
        """Write all output states to the NI-9477."""
        if len(states) != NI9477_CHANNEL_COUNT:
            raise ValueError(
                f"NI9477 expects {NI9477_CHANNEL_COUNT} channel states, got {len(states)}."
            )

        next_states = [bool(state) for state in states]
        async with self._write_lock:
            try:
                await asyncio.to_thread(self._task.write, next_states, auto_start=True)
            except Exception:
                logger.exception(
                    f"Could not write output state to NI9477 module '{self.module}'."
                )
                return False
            self._channel_states = next_states
        return True

    def get_channel_state(self, channel: str | int) -> bool:
        """Return the cached output state for one Flowchem channel."""
        return self._channel_states[self._channel_index(channel)]

    def get_channel_states(self) -> list[bool]:
        """Return cached output states for all channels."""
        return self._channel_states.copy()

    def close(self) -> None:
        """Close the underlying NI-DAQmx task."""
        try:
            self._task.close()
        except AttributeError:
            return

    def __del__(self) -> None:
        self.close()

    @staticmethod
    def default_line_names(module: str) -> list[str]:
        """Return conventional NI-9477 physical line names."""
        return [f"{module}/port0/line{index}" for index in range(NI9477_CHANNEL_COUNT)]

    @staticmethod
    def _channel_index(channel: str | int) -> int:
        try:
            channel_number = int(channel)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "NI9477 channel must be an integer from 1 to 32."
            ) from error
        if not 1 <= channel_number <= NI9477_CHANNEL_COUNT:
            raise ValueError("NI9477 channel must be between 1 and 32.")
        return channel_number - 1

    @classmethod
    def _resolve_module(cls, system: Any, module: str | None) -> Any:
        devices = list(system.local().devices)
        ni9477_devices = [device for device in devices if cls._is_ni9477(device)]

        if module is not None:
            try:
                selected = next(device for device in devices if device.name == module)
            except StopIteration as error:
                raise InvalidConfigurationError(
                    f"NI module '{module}' was not found by NI-DAQmx. "
                    "Check the NI MAX device name and USB connection.",
                ) from error
            if not cls._is_ni9477(selected):
                raise InvalidConfigurationError(
                    f"NI module '{module}' is '{getattr(selected, 'product_type', 'unknown')}', not an NI-9477.",
                )
            return selected

        if len(ni9477_devices) == 1:
            return ni9477_devices[0]
        if not ni9477_devices:
            raise InvalidConfigurationError("No NI-9477 module was found by NI-DAQmx.")
        module_names = ", ".join(device.name for device in ni9477_devices)
        raise InvalidConfigurationError(
            f"Multiple NI-9477 modules were found ({module_names}); set the 'module' config value explicitly.",
        )

    @classmethod
    def _discover_line_names(cls, module_device: Any, module_name: str) -> list[str]:
        line_names = _physical_channel_names(getattr(module_device, "do_lines", ()))
        if len(line_names) == NI9477_CHANNEL_COUNT:
            return sorted(line_names, key=_line_sort_key)
        logger.warning(
            f"Could not discover exactly {NI9477_CHANNEL_COUNT} NI9477 DO lines for '{module_name}'. "
            "Using conventional port0/line0:31 names.",
        )
        return cls.default_line_names(module_name)

    @staticmethod
    def _is_ni9477(device: Any) -> bool:
        return "9477" in str(getattr(device, "product_type", "")).replace("-", "")


def _import_nidaqmx() -> tuple[Any, Any, Any]:
    try:
        nidaqmx = importlib.import_module("nidaqmx")
        system = importlib.import_module("nidaqmx.system").System
        constants = importlib.import_module("nidaqmx.constants")
    except ImportError as error:
        raise InvalidConfigurationError(
            "NI9477 support requires the optional NI dependency and NI-DAQmx driver. "
            'Install the Python package with `python -m pip install "flowchem[ni]"` '
            "or `python -m pip install nidaqmx`, then verify the device in NI MAX.",
        ) from error
    return nidaqmx, system, constants.LineGrouping


def _physical_channel_names(collection: Any) -> list[str]:
    for attribute in ("channel_names", "names"):
        names = getattr(collection, attribute, None)
        if names is not None:
            return [str(name) for name in names]
    try:
        return [str(getattr(channel, "name", channel)) for channel in collection]
    except TypeError:
        return []


def _line_sort_key(line_name: str) -> tuple[str, int]:
    prefix, _, suffix = line_name.rpartition("line")
    try:
        return prefix, int(suffix)
    except ValueError:
        return line_name, -1
