from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import BackgroundTasks

from flowchem.components.analytics.nmr import NMRControl

if TYPE_CHECKING:
    from .spinsolve import Spinsolve


class SpinsolveControl(NMRControl):
    hw_device: Spinsolve  # for typing's sake

    def __init__(self, name: str, hw_device: Spinsolve) -> None:  # type: ignore
        """HPLC Control component. Sends methods, starts run, do stuff."""
        super().__init__(name, hw_device)
        # Solvent
        self.add_api_route("/solvent", self.hw_device.get_solvent, methods=["GET"])
        self.add_api_route("/solvent", self.hw_device.set_solvent, methods=["PUT"])
        # Sample name
        self.add_api_route("/sample-name", self.hw_device.get_sample, methods=["GET"])
        self.add_api_route("/sample-name", self.hw_device.set_sample, methods=["PUT"])
        # User data
        self.add_api_route("/user-data", self.hw_device.get_user_data, methods=["GET"])
        self.add_api_route("/user-data", self.hw_device.set_user_data, methods=["PUT"])
        # Protocols
        self.add_api_route(
            "/protocol-list",
            self.hw_device.list_protocols,
            methods=["GET"],
        )
        self.add_api_route(
            "/spectrum-folder",
            self.hw_device.get_result_folder,
            methods=["GET"],
        )
        self.add_api_route(
            "/is-busy",
            self.hw_device.is_protocol_running,
            methods=["GET"],
        )

    async def acquire_spectrum(
        self,
        background_tasks: BackgroundTasks,
        protocol="H",
        options=None,
    ) -> int:
        """Acquire an NMR spectrum.

        Return an ID to be passed to get_result_folder, it will return the result folder after acquisition end.
        """
        return await self.hw_device.run_protocol(
            name=protocol,
            background_tasks=background_tasks,
            options=options,
        )

    async def stop(self):
        return await self.hw_device.abort()
