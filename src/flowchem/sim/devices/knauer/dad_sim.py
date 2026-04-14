"""Simulated Knauer DAD (diode-array detector)."""

from __future__ import annotations

from loguru import logger

from flowchem.sim.devices.knauer._knauer_base import SimulatedKnauerEthernetDevice
from flowchem.devices.knauer.dad import KnauerDAD


class KnauerDADSim(SimulatedKnauerEthernetDevice, KnauerDAD):
    """
    Simulated Knauer DAD.

    The real KnauerDAD uses the proprietary NDA package ``flowchem_knauer``
    and communicates over TCP.  This sim:
    - inherits ``SimulatedKnauerEthernetDevice`` to bypass TCP entirely
    - stubs ``KnauerDADCommands`` so the NDA guard never fires
    - keeps full KnauerDAD logic intact (all component methods work)

    State
    -----
    _sim_wavelengths  : dict   channel (1-4) → wavelength nm
    _sim_signals      : dict   channel (1-4) → float signal (µAU)
    _sim_lamps        : dict   lamp name → str state ("0"=OFF, "1"=ON)
    _sim_bandwidth    : int    bandwidth nm
    _sim_integ_time   : int    integration time ms
    _sim_serial       : str    serial number string
    """

    class _StubDADCommands:
        """Minimal stub so KnauerDAD.__init__ succeeds without the NDA package."""

        LAMP = "LAMP{lamp}:{state}"
        SERIAL = "SERIAL"
        IDENTIFY = "IDENTIFY"
        INFO = "INFO"
        STATUS = "STATUS"
        LOCAL = "LOCAL"
        REMOTE = "REMOTE"
        SHUTTER = "SHUTTER:{state}"
        SIGNAL_TYPE = "SIGNAL_TYPE:{state}"
        WAVELENGTH = "WL{channel}:{wavelength}"
        SIGNAL = "SIG{channel}:{signal}"
        INTEGRATION_TIME = "INTTIME:{time}"
        BANDWIDTH = "BW:{bandwidth}"

    def __init__(
        self,
        ip_address=None,
        mac_address=None,
        name: str | None = None,
        turn_on_d2: bool = False,
        turn_on_halogen: bool = False,
        display_control: bool = True,
    ):
        # Bypass both KnauerEthernetDevice and KnauerDAD __init__ network/NDA logic.
        from flowchem.devices.flowchem_device import FlowchemDevice
        from flowchem.components.device_info import DeviceInfo

        FlowchemDevice.__init__(self, name or "sim-dad")

        self.eol = b"\n\r"
        self._d2 = turn_on_d2
        self._hal = turn_on_halogen
        self._state_d2 = False
        self._state_hal = False
        self._control = display_control
        self.cmd = self._StubDADCommands()

        self.device_info = DeviceInfo(
            manufacturer="Knauer",
            model="SimulatedDAD",
            serial_number="SIM-DAD",
        )

        # Simulated state
        self._sim_wavelengths: dict[int, int] = {1: 254, 2: 280, 3: 360, 4: 450}
        self._sim_signals: dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self._sim_lamps: dict[str, str] = {"d2": "0", "hal": "0"}
        self._sim_bandwidth: int = 8
        self._sim_integ_time: int = 100
        self._sim_serial: str = "SIM-DAD-00001"
        logger.info(f"[SIM] KnauerDAD '{self.name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "KnauerDADSim":
        config.pop("ip_address", None)
        config.pop("mac_address", None)
        return cls(
            name=config.pop("name", "sim-dad"),
            turn_on_d2=bool(config.pop("turn_on_d2", False)),
            turn_on_halogen=bool(config.pop("turn_on_halogen", False)),
        )

    # ------------------------------------------------------------------
    # Override the single network method — all KnauerDAD logic calls this
    # ------------------------------------------------------------------

    async def _send_and_receive(self, message: str) -> str:
        logger.debug(f"[SIM] KnauerDAD ← {message!r}")
        return self._handle_command(message)

    def _handle_command(self, message: str) -> str:
        msg = message.strip()

        # LAMP
        if msg.startswith("LAMP"):
            # Format: "LAMP_D2:?" or "LAMP_HAL:1"
            lamp_key = "d2" if "D2" in msg else "hal"
            if msg.endswith("?") or msg.endswith(":?"):
                return self._sim_lamps[lamp_key]
            state = msg.split(":")[-1]
            self._sim_lamps[lamp_key] = state
            return state

        # SERIAL
        if msg == "SERIAL":
            return self._sim_serial

        # IDENTIFY / INFO / STATUS
        if msg == "IDENTIFY":
            return "3,KNAUER,PDA-1,SIM-DAD,2,01"
        if msg == "INFO":
            return "1024,UV-VIS,1,2020,1,,1.0,1.0,,1.0"
        if msg == "STATUS":
            d2 = self._sim_lamps["d2"]
            hal = self._sim_lamps["hal"]
            return f"0,{d2},{hal},0,0,0,0,0,0,0,0"

        # LOCAL / REMOTE
        if msg in ("LOCAL", "REMOTE"):
            return "OK"

        # WAVELENGTH  WL<ch>:value or WL<ch>:?
        if msg.startswith("WL"):
            rest = msg[2:]  # "1:254" or "1:?"
            ch_str, val_str = rest.split(":", 1)
            ch = int(ch_str)
            if val_str == "?":
                return str(self._sim_wavelengths.get(ch, 254))
            self._sim_wavelengths[ch] = int(val_str)
            return val_str

        # SIGNAL  SIG<ch>:? or SIG<ch>:0
        if msg.startswith("SIG"):
            rest = msg[3:]
            ch_str, val_str = rest.split(":", 1)
            ch = int(ch_str)
            if val_str == "?":
                raw = int(self._sim_signals.get(ch, 0.0) * 10000)
                return f"SIG{ch}:{raw}"
            self._sim_signals[ch] = float(val_str)
            return val_str

        # INTEGRATION TIME  INTTIME:<val> or INTTIME:?
        if msg.startswith("INTTIME"):
            val_str = msg.split(":")[-1]
            if val_str == "?":
                return str(self._sim_integ_time)
            self._sim_integ_time = int(val_str)
            return val_str

        # BANDWIDTH  BW:<val> or BW:?
        if msg.startswith("BW"):
            val_str = msg.split(":")[-1]
            if val_str == "?":
                return str(self._sim_bandwidth)
            self._sim_bandwidth = int(val_str)
            return val_str

        # SHUTTER / SIGNAL_TYPE
        if msg.startswith("SHUTTER") or msg.startswith("SIGNAL_TYPE"):
            return "OK"

        logger.debug(f"[SIM] KnauerDAD unhandled: {msg!r}")
        return "OK"

    # ------------------------------------------------------------------
    # Override initialize to register components without NDA package
    # ------------------------------------------------------------------

    async def initialize(self):
        from flowchem.devices.knauer.dad_component import (
            DADChannelControl,
            KnauerDADLampControl,
        )

        logger.info("[SIM] KnauerDAD skipping TCP connection.")

        # Replicate KnauerDAD.initialize() component registration
        self.components = [
            KnauerDADLampControl("d2", self),
            KnauerDADLampControl("hal", self),
        ]
        self.components.extend(
            [DADChannelControl(f"channel{n + 1}", self, n + 1) for n in range(4)]
        )
