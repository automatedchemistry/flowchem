"""Simulated Magritek Spinsolve NMR spectrometer."""

from __future__ import annotations

from typing import Any, cast

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo


class SpinsolveSim(FlowchemDevice):
    """
    Simulated Magritek Spinsolve NMR spectrometer.

    The real Spinsolve connects via asyncio TCP to a running Spinsolve application
    and communicates through XML messages.  This sim bypasses all of that by
    subclassing FlowchemDevice directly.

    State
    -----
    _sim_solvent    : str   current solvent
    _sim_sample     : str   current sample name
    _sim_protocols  : dict  available protocols (static)
    _sim_running    : bool  whether a protocol is running
    _sim_results    : list  accumulated result folder paths
    """

    def __init__(
        self,
        host="127.0.0.1",
        port=13000,
        name=None,
        xml_schema=None,
        data_folder=None,
        solvent="Chloroform-d1",
        sample_name="Unnamed automated experiment",
        remote_to_local_mapping=None,
    ):
        super().__init__(name or "sim-spinsolve")
        self.device_info = DeviceInfo(
            manufacturer="Magritek",
            model="SimulatedSpinsolve",
            version="1.18.1.3062",
        )
        self._sim_solvent: str = solvent or "Chloroform-d1"
        self._sim_sample: str = sample_name or "Unnamed"
        self._sim_data_folder: str = data_folder or "/tmp/spinsolve"
        self._sim_running: bool = False
        self._sim_results: list = []
        self._sim_user_data: dict[str, str] = {"control_software": "flowchem"}
        self._sim_protocols: dict = {
            "PROTON": {"Number": ["1", "4", "8", "16"]},
            "CARBON": {},
            "FLUORINE": {},
        }
        logger.info(f"[SIM] Spinsolve '{self.name}' initialized.")

    @classmethod
    def from_config(cls, **config) -> "SpinsolveSim":
        return cls(
            host=config.pop("host", "127.0.0.1"),
            port=int(config.pop("port", 13000)),
            name=config.pop("name", "sim-spinsolve"),
            data_folder=config.pop("data_folder", None),
            solvent=config.pop("solvent", "Chloroform-d1"),
            sample_name=config.pop("sample_name", "Unnamed"),
        )

    async def initialize(self):
        from flowchem.devices.magritek.spinsolve_control import SpinsolveControl

        logger.info("[SIM] Spinsolve skipping TCP connection.")
        self.components.append(SpinsolveControl("nmr-control", cast(Any, self)))

    # Public API used by SpinsolveControl
    async def get_solvent(self) -> str:
        return self._sim_solvent

    async def set_solvent(self, solvent: str):
        self._sim_solvent = solvent

    async def get_sample(self) -> str:
        return self._sim_sample

    async def set_sample(self, sample: str):
        self._sim_sample = sample

    async def get_user_data(self) -> dict[str, str]:
        return dict(self._sim_user_data)

    async def set_user_data(self, data: dict[str, str]):
        self._sim_user_data = dict(data)

    async def set_data_folder(self, location: str):
        if location:
            self._sim_data_folder = location

    async def is_protocol_running(self) -> bool:
        return self._sim_running

    def list_protocols(self) -> list[str]:
        return list(self._sim_protocols.keys())

    async def run_protocol(self, name, background_tasks=None, options=None) -> int:
        name = name.upper()
        if name not in self._sim_protocols:
            logger.warning(f"[SIM] Protocol {name!r} not available.")
            return -1
        self._sim_running = True
        result_id = len(self._sim_results)
        self._sim_results.append(f"{self._sim_data_folder}/{name}_{result_id}")
        self._sim_running = False
        logger.info(f"[SIM] Spinsolve protocol {name!r} completed.")
        return result_id

    async def get_result_folder(self, result_id=None) -> str:
        if result_id is None:
            result_id = -1
        try:
            return str(self._sim_results[result_id])
        except IndexError:
            return ""

    async def abort(self):
        self._sim_running = False
