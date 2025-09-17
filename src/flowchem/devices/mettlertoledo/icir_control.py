from __future__ import annotations

from typing import TYPE_CHECKING
from loguru import logger

from flowchem.components.analytics.ir import IRControl, IRSpectrum

if TYPE_CHECKING:
    from .icir import IcIR


class IcIRControl(IRControl):
    """
    IcIR Control component for handling IR spectrometer operations.

    Attributes:
        hw_device (IcIR): The hardware device for the IR spectrometer.
    """
    hw_device: IcIR  # for typing's sake

    def __init__(self, name: str, hw_device: IcIR) -> None:  # type:ignore
        """
        Initialize the IcIRControl component.

        Args:
            name (str): The name of the component.
            hw_device (IcIR): The hardware device instance for controlling the IR spectrometer.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/spectrum-count", self.spectrum_count, methods=["GET"])

    async def acquire_spectrum(self, treated: bool = True) -> IRSpectrum:
        """
        Acquire an IR spectrum from the instrument.

        This method retrieves the most recent infrared (IR) spectrum acquired by the device.
        Depending on the `treated` parameter, it can return either a processed spectrum with background subtraction
        or a raw, unprocessed spectrum.

        The acquisition process works as follows:
        - If `treated` is True, the method returns a spectrum where background subtraction has been performed,
          providing a clean signal suitable for analysis. The treated spectrum is retrieved from the device's
          OPC UA node specified by `SPECTRA_TREATED` ("ns=2;s=Local.iCIR.Probe1.SpectraTreated").
        - If `treated` is False, the method returns the raw, unprocessed spectrum directly from the device,
          without any background correction. The raw spectrum is retrieved from the OPC UA node specified by
          `SPECTRA_RAW` ("ns=2;s=Local.iCIR.Probe1.SpectraRaw").

        Args:
            treated (bool): If True, perform background subtraction and return the treated spectrum.
                            If False, return the raw scan without any processing.

        Returns:
            IRSpectrum: The acquired IR spectrum, either treated or raw.
        """
        if treated:
            return await self.hw_device.last_spectrum_treated()
        else:
            return await self.hw_device.last_spectrum_raw()

    async def spectrum_count(self) -> int:
        """
        Get the count of acquired spectra.

        Returns:
            int: The number of spectra acquired. Returns -1 if the count is None.
        """
        count = await self.hw_device.sample_count()
        if count is not None:
            return count
        else:
            logger.warning("The spectrum count return a 'None' value! This reply was replaced to the int -1.")
            return -1

    async def stop(self):
        """
        Stop the ongoing IR experiment.

        Returns:
            bool: True if the experiment was successfully stopped, False otherwise.
        """
        return await self.hw_device.stop_experiment()
