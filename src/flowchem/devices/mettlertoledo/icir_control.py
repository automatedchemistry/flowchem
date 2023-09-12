from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.analytics.ir import IRControl
from flowchem.components.analytics.ir import IRSpectrum

if TYPE_CHECKING:
    from .icir import IcIR


class IcIRControl(IRControl):
    hw_device: IcIR  # for typing's sake

    def __init__(self, name: str, hw_device: IcIR):  # type:ignore
        """HPLC Control component. Sends methods, starts run, do stuff."""
        super().__init__(name, hw_device)
        self.add_api_route("/spectrum-count", self.spectrum_count, methods=["GET"])

    async def acquire_spectrum(self, treated: bool = True) -> IRSpectrum:
        """
        Acquire an IR spectrum.

        Background subtraction performed if treated=True, else a raw scan is returned.
        """
        if treated:
            return await self.hw_device.last_spectrum_treated()
        else:
            return await self.hw_device.last_spectrum_raw()

    async def spectrum_count(self) -> int:
        count = await self.hw_device.sample_count()
        if count is not None:
            return count
        else:
            return -1

    async def stop(self):
        return await self.hw_device.stop_experiment()
