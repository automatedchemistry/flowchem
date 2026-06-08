"""Simulated Knauer Autosampler AS 6.1L."""

from __future__ import annotations

from typing import Any, cast

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo


class KnauerAutosamplerSim(FlowchemDevice):
    """
    Simulated Knauer Autosampler AS 6.1L.

    The real device uses a proprietary NDA package (NDA_knauer_AS) and
    communicates either via TCP or serial.  This sim subclasses
    FlowchemDevice directly and provides in-memory implementations of
    every method called by the four components.

    State
    -----
    _sim_errors           : str    current error string ("No Error." when clear)
    _sim_status           : str    device status string key
    _sim_injection_valve  : str    injection valve position ("LOAD" | "INJECT")
    _sim_syringe_valve    : str    syringe valve position ("NEEDLE"|"WASH"|"WASTE")
    _sim_needle_h         : str    needle horizontal position
    _sim_needle_v         : str    needle vertical position ("UP" | "DOWN")
    _sim_tray             : tuple  (tray, row) last tray move
    _sim_aspirated_ul     : float  cumulative aspirated volume µL
    _sim_dispensed_ul     : float  cumulative dispensed volume µL
    _sim_syringe_volume   : int    syringe volume in µL
    _sim_tray_temp_sp     : int    tray temperature setpoint °C
    """

    def __init__(
        self,
        name: str | None = None,
        ip_address: str = "",
        autosampler_id: int | None = 61,
        port: str | None = None,
        _syringe_volume: str = "250 uL",
        tray_type: str = "TRAY_48_VIAL",
        **kwargs,
    ):
        super().__init__(name or "sim-autosampler")
        self.autosampler_id = autosampler_id
        self.tray_type = tray_type.upper()
        self._syringe_volume = 250  # µL

        self.device_info = DeviceInfo(
            manufacturer="Knauer",
            model="SimulatedAutosampler",
            serial_number="SIM-AS",
        )

        # Simulated state
        self._sim_errors: str = "No Error."
        self._sim_status: str = "IDLE"
        self._sim_injection_valve: str = "LOAD"
        self._sim_syringe_valve: str = "WASTE"
        self._sim_needle_h: str = "WASTE"
        self._sim_needle_v: str = "UP"
        self._sim_tray: tuple = ("", 0)
        self._sim_aspirated_ul: float = 0.0
        self._sim_dispensed_ul: float = 0.0
        self._sim_tray_temp_sp: int = 20
        logger.info(f"[SIM] KnauerAutosampler '{self.name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "KnauerAutosamplerSim":
        config.pop("ip_address", None)
        config.pop("port", None)
        return cls(
            name=config.pop("name", "sim-autosampler"),
            autosampler_id=int(config.pop("autosampler_id", 61)),
            tray_type=config.pop("tray_type", "TRAY_48_VIAL"),
            _syringe_volume=config.pop("_syringe_volume", "250 uL"),
        )

    async def initialize(self):
        from flowchem.devices.knauer.knauer_autosampler_component import (
            AutosamplerGantry3D,
            AutosamplerPump,
            AutosamplerSyringeValve,
            AutosamplerInjectionValve,
        )

        self.components.extend(
            [
                AutosamplerGantry3D("gantry3D", cast(Any, self)),
                AutosamplerPump("pump", cast(Any, self)),
                AutosamplerSyringeValve("syringe_valve", cast(Any, self)),
                AutosamplerInjectionValve("injection_valve", cast(Any, self)),
            ]
        )
        logger.info(f"[SIM] KnauerAutosampler '{self.name}' components registered.")

    # ------------------------------------------------------------------
    # Public API called by components
    # ------------------------------------------------------------------

    async def get_errors(self) -> str:
        return self._sim_errors

    async def reset_errors(self):
        self._sim_errors = "No Error."

    async def get_status(self) -> str:
        return self._sim_status

    async def injector_valve_position(self, port: str | None = None) -> str:
        if port is not None:
            self._sim_injection_valve = port.upper()
            logger.debug(f"[SIM] Injection valve → {port}")
            return port.upper()
        return self._sim_injection_valve

    async def syringe_valve_position(self, port: str | None = None) -> str:
        if port is not None:
            self._sim_syringe_valve = port.upper()
            logger.debug(f"[SIM] Syringe valve → {port}")
            return port.upper()
        return self._sim_syringe_valve

    async def set_raw_position(
        self, position: str | None = None, target_component: str | None = None
    ) -> str:
        match target_component:
            case "injection_valve":
                return await self.injector_valve_position(port=position)
            case "syringe_valve":
                return await self.syringe_valve_position(port=position)
            case _:
                raise RuntimeError(f"Unknown valve type: {target_component}")

    async def get_raw_position(self, target_component: str | None = None) -> str:
        match target_component:
            case "injection_valve":
                return await self.injector_valve_position(port=None)
            case "syringe_valve":
                return await self.syringe_valve_position(port=None)
            case _:
                raise RuntimeError(f"Unknown valve type: {target_component}")

    async def _move_needle_horizontal(
        self,
        needle_position: str | None,
        plate: str | None = None,
        well: int | None = None,
    ) -> bool:
        self._sim_needle_h = str(needle_position)
        logger.debug(
            f"[SIM] Needle horizontal → {needle_position}, plate={plate}, well={well}"
        )
        return True

    async def _move_needle_vertical(self, move_to: str) -> bool:
        self._sim_needle_v = move_to.upper()
        logger.debug(f"[SIM] Needle vertical → {move_to}")
        return True

    async def _move_tray(self, tray_type: str, sample_position: str | int) -> bool:
        self._sim_tray = (tray_type, sample_position)
        logger.debug(f"[SIM] Tray moved → tray={tray_type}, pos={sample_position}")
        return True

    async def aspirate(self, volume: float, flow_rate: float | None = None) -> bool:
        self._sim_aspirated_ul += volume * 1000
        logger.debug(
            f"[SIM] Aspirated {volume} mL (total: {self._sim_aspirated_ul} µL)"
        )
        return True

    async def dispense(self, volume: float, flow_rate: float | None = None) -> bool:
        self._sim_dispensed_ul += volume * 1000
        logger.debug(
            f"[SIM] Dispensed {volume} mL (total: {self._sim_dispensed_ul} µL)"
        )
        return True

    async def syringe_volume(self, volume: int | None = None) -> int:
        if volume is not None:
            self._syringe_volume = volume
        return self._syringe_volume

    async def set_tray_temperature(self, setpoint: int | None = None) -> int:
        if setpoint is not None:
            self._sim_tray_temp_sp = setpoint
        return self._sim_tray_temp_sp

    async def measure_tray_temperature(self) -> int:
        return self._sim_tray_temp_sp
