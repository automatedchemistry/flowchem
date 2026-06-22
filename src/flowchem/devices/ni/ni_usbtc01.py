"""NI USB-TC01 single-channel thermocouple temperature sensor via NI-DAQmx."""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.ni._common import import_nidaqmx, resolve_ni_device
from flowchem.devices.ni.ni_usbtc01_component import TC01TemperatureSensor
from flowchem.utils.people import samuel_saraiva

_VALID_TC_TYPES = ("J", "K", "T", "E", "N", "B", "R", "S")


class NIUSBTC01(FlowchemDevice):
    """NI USB-TC01 single-channel thermocouple temperature sensor."""

    def __init__(
        self,
        module: str,
        task: Any,
        thermocouple_type: str = "K",
        serial_number: str | int = "unknown",
        name: str = "",
    ) -> None:
        super().__init__(name)
        self.module = module
        self._task = task
        self._thermocouple_type = thermocouple_type
        self._read_lock = asyncio.Lock()

        self.device_info = DeviceInfo(
            authors=[samuel_saraiva],
            manufacturer="National Instruments",
            model="NI USB-TC01",
            serial_number=serial_number,
            additional_info={
                "module": module,
                "thermocouple_type": thermocouple_type,
            },
        )

    @classmethod
    def from_config(
        cls,
        module: str | None = None,
        thermocouple_type: str = "K",
        name: str = "",
    ) -> "NIUSBTC01":
        """Create an NIUSBTC01 from Flowchem TOML configuration."""
        nidaqmx, system, constants = import_nidaqmx()

        tc_type_upper = thermocouple_type.upper()
        if tc_type_upper not in _VALID_TC_TYPES:
            from flowchem.utils.exceptions import InvalidConfigurationError

            raise InvalidConfigurationError(
                f"Invalid thermocouple_type '{thermocouple_type}'. "
                f"Valid values: {list(_VALID_TC_TYPES)}."
            )

        module_device = resolve_ni_device(
            system,
            module,
            product_fragment="USBTC01",
            device_label="NI USB-TC01",
        )
        module_name = module_device.name
        channel = f"{module_name}/ai0"

        tc_type = getattr(constants.ThermocoupleType, tc_type_upper)
        cjc_source = constants.CJCSource.BUILT_IN

        task = nidaqmx.Task()
        task.ai_channels.add_ai_thrmcpl_chan(
            channel,
            thermocouple_type=tc_type,
            cjc_source=cjc_source,
        )

        return cls(
            module=module_name,
            task=task,
            thermocouple_type=tc_type_upper,
            serial_number=getattr(module_device, "serial_num", "unknown"),
            name=name,
        )

    async def initialize(self) -> None:
        """Register the temperature sensor component."""
        self.components.append(TC01TemperatureSensor("temperature", self))
        logger.info(
            f"Connected to NI USB-TC01 '{self.module}' "
            f"with type-{self._thermocouple_type} thermocouple."
        )

    async def read_temperature(self) -> float:
        """Read the thermocouple temperature in degrees Celsius."""
        async with self._read_lock:
            value = await asyncio.to_thread(self._task.read)
        return float(value)

    def close(self) -> None:
        """Close the underlying NI-DAQmx task."""
        try:
            self._task.close()
        except AttributeError:
            return

    def __del__(self) -> None:
        self.close()
