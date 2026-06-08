"""Simulated Vapourtec R2 reactor module."""

from __future__ import annotations

from typing import Any, cast

import pint

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo


class _StubR2Commands:
    """Minimal stub for VapourtecR2Commands (which is under NDA)."""

    VERSION = "V"
    GET_SYSTEM_TYPE = "ST"
    GET_STATUS = "GS"
    SET_FLOWRATE = "SF {pump} {rate_in_ul_min}"
    SET_TEMPERATURE = "ST {channel} {temperature_in_C} {ramp_rate}"
    SET_MAX_PRESSURE = "SMP {max_p_in_mbar}"
    SET_UV150 = "UV {power_percent} {heater_on}"
    KEY_PRESS = "KP {keycode}"
    POWER_ON = "PON"
    POWER_OFF = "POFF"
    HISTORY_TEMPERATURE = "HT"
    HISTORY_PRESSURE = "HP"
    HISTORY_FLOW = "HF"


class R2Sim(FlowchemDevice):
    """
    Simulated Vapourtec R2 reactor module.

    The real R2 uses a proprietary NDA command package (flowchem_vapourtec)
    and communicates over serial.  This sim bypasses both by subclassing
    FlowchemDevice directly and providing stub implementations of every
    method that R2 components call.

    State
    -----
    _sim_flowrate  : dict   pump → µL/min
    _sim_temp      : dict   channel → °C
    _sim_pressure  : tuple  (pumpA_mbar, pumpB_mbar, sys_mbar)
    _sim_running   : bool
    _sim_uv        : int    UV intensity %
    _sim_valves    : int    valve bitmap
    """

    def __init__(
        self,
        name: str = "",
        rt_temp: float = 25.0,
        min_temp=None,
        max_temp=None,
        min_pressure: float = 1000,
        max_pressure: float = 50000,
        **config,
    ):
        super().__init__(name)
        self.device_info = DeviceInfo(
            manufacturer="Vapourtec",
            model="SimulatedR2",
            version="SIM-1.0",
        )
        self.cmd = _StubR2Commands()
        self._serial = None
        self._serial_lock = None

        self._sim_flowrate: dict = {"A": 0, "B": 0}
        self._sim_temp: dict = {0: rt_temp, 1: rt_temp, 2: rt_temp, 3: rt_temp}
        self._sim_pressure: tuple = (0, 0, 0)
        self._sim_running: bool = False
        self._sim_uv: int = 0
        self._sim_valves: int = 0
        logger.info(f"[SIM] R2 '{name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "R2Sim":
        config.pop("port", None)
        return cls(name=config.pop("name", "sim-r2"), **config)

    async def initialize(self):
        """Build the same component list as the real R2.initialize()."""
        from flowchem.components.technical.temperature import TempRange
        from flowchem import ureg
        from flowchem.devices.vapourtec.r2_components_control import (
            R2GeneralPressureSensor,
            R2GeneralSensor,
            R2HPLCPump,
            R2InjectionValve,
            R2MainSwitch,
            R2PumpPressureSensor,
            R2TwoPortValve,
            UV150PhotoReactor,
            R4Reactor,
        )

        min_t: pint.Quantity = ureg.Quantity("-40 degC")
        max_t: pint.Quantity = ureg.Quantity("80 degC")
        temp_range = TempRange(min=min_t, max=max_t)

        self.components.extend(
            [
                R2MainSwitch("Power", cast(Any, self)),
                R2GeneralPressureSensor("PressureSensor", cast(Any, self)),
                R2GeneralSensor("GSensor2", cast(Any, self)),
                UV150PhotoReactor("PhotoReactor", cast(Any, self)),
                R2HPLCPump("Pump_A", cast(Any, self), "A"),
                R2HPLCPump("Pump_B", cast(Any, self), "B"),
                R2TwoPortValve("ReagentValve_A", cast(Any, self), 0),
                R2TwoPortValve("ReagentValve_B", cast(Any, self), 1),
                R2TwoPortValve("CollectionValve", cast(Any, self), 4),
                R2InjectionValve("InjectionValve_A", cast(Any, self), 2),
                R2InjectionValve("InjectionValve_B", cast(Any, self), 3),
                R2PumpPressureSensor("PumpSensor_A", cast(Any, self), 0),
                R2PumpPressureSensor("PumpSensor_B", cast(Any, self), 1),
            ]
        )
        for n in range(4):
            self.components.append(
                R4Reactor(f"reactor-{n+1}", cast(Any, self), n, temp_range)
            )

    # Stub implementations of every method called by R2 components
    async def write_and_read_reply(self, command: str) -> str:
        logger.debug(f"[SIM] R2 ← {command!r}")
        cmd = command.strip().upper()

        if cmd == "V":
            return "SIM-1.0"
        if cmd == "ST":
            return "SIM 0"
        if cmd == "GS":
            fa = self._sim_flowrate["A"]
            fb = self._sim_flowrate["B"]
            vb = f"{self._sim_valves:05b}"
            temps = " ".join(f"{self._sim_temp[i]*10:.0f}" for i in range(4))
            state = "1" if self._sim_running else "0"
            return f"{state} {fa} {fb} 0 0 0 {vb} {temps} 0 0 0 0 0 0 0"
        if cmd.startswith("SF"):
            parts = command.split()
            pump = "A" if parts[1] == "0" else "B"
            self._sim_flowrate[pump] = int(parts[2])
            return "OK"
        if cmd.startswith("ST "):
            parts = command.split()
            ch = int(parts[1])
            t = float(parts[2])
            self._sim_temp[ch] = t
            return "OK"
        if cmd.startswith("SMP"):
            return "OK"
        if cmd.startswith("UV"):
            parts = command.split()
            self._sim_uv = int(parts[1])
            return "OK"
        if cmd.startswith("KP"):
            key = command.split()[-1]
            self._sim_valves = int(key) if key.isdigit() else 0
            return "OK"
        if cmd == "PON":
            self._sim_running = True
            return "OK"
        if cmd == "POFF":
            self._sim_running = False
            return "OK"
        if cmd == "HT":
            t_str = ",".join(f"0,{self._sim_temp[i]*10:.0f}" for i in range(4))
            return f"0,{t_str}"
        if cmd == "HP":
            pa, pb, ps = self._sim_pressure
            return f"0,{pa//10},{pb//10},{ps//10}"
        if cmd == "HF":
            fa = self._sim_flowrate["A"]
            fb = self._sim_flowrate["B"]
            return f"0,{fa},{fb}"

        logger.debug(f"[SIM] R2 unhandled: {command!r}")
        return "OK"

    async def version(self) -> str:
        return await self.write_and_read_reply(self.cmd.VERSION)

    async def get_status(self):
        from flowchem.devices.vapourtec.r2 import R2

        raw = await self.write_and_read_reply(self.cmd.GET_STATUS)
        return R2.AllComponentStatus._make(raw.split(" "))

    async def get_current_temperature(self, channel: int) -> float:
        return self._sim_temp.get(channel, 25.0)

    async def get_current_pressure(self, pump_code: int = 2):
        from flowchem import ureg

        return self._sim_pressure[pump_code] * ureg.mbar

    async def get_current_flow(self, pump_code: str) -> float:
        return float(self._sim_flowrate.get(pump_code, 0))

    async def set_flowrate(self, pump: str, flowrate: str):
        from flowchem import ureg

        q: pint.Quantity = ureg.Quantity(flowrate)
        self._sim_flowrate[pump] = round(q.m_as("ul/min"))

    async def set_temperature(self, channel, temp, heating=None, ramp_rate="80"):
        self._sim_temp[channel] = (
            temp.m_as("degC") if hasattr(temp, "m_as") else float(temp)
        )

    async def set_pressure_limit(self, pressure: str):
        pass

    async def set_UV150(self, power: int):
        self._sim_uv = power

    async def trigger_key_press(self, keycode: str):
        pass

    async def power_on(self):
        self._sim_running = True

    async def power_off(self):
        self._sim_running = False

    async def get_valve_position(self, valve_code: int) -> str:
        bitmap = self._sim_valves
        return list(reversed(f"{bitmap:05b}"))[valve_code]

    async def get_pressure_history(self):
        return self._sim_pressure

    async def get_state(self) -> str:
        return "Running" if self._sim_running else "Off"
