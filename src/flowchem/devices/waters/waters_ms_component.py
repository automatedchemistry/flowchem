"""
WatersMSControl provides a device-specific extension of MSControl for Waters Xevo MS.

This control class delegates MS acquisition to the underlying hardware driver (`WatersMS`)
by passing sample metadata and optional conversion instructions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.analytics.ms import MSControl

if TYPE_CHECKING:
    from flowchem.devices import WatersMS


class WatersMSControl(MSControl):
    """
    Control layer for Waters Xevo MS, extending the generic MSControl.

    This class is responsible for initiating a mass spectrometry run using the connected
    WatersMS hardware device. It provides an interface compatible with FlowChem's component system.

    Attributes:
        hw_device (WatersMS): Reference to the associated WatersMS hardware device.
    """
    hw_device: WatersMS  # for typing's sake

    def __init__(self, name: str, hw_device: WatersMS) -> None:
        """Device-specific initialization."""
        super().__init__(name, hw_device)

    async def run_sample(self,
                         sample_name: str,
                         run_duration: int = 0,
                         queue_name: str = "next.txt",
                         do_conversion: bool = False,
                         output_dir: str = "PATH/TO/open_format_ms"):
        """
        Trigger a mass spectrometry sample run.

        Args:
            sample_name (str): Name to assign to the sample (used in queue file and filename).
            run_duration (int): Estimated duration of the acquisition in seconds.
            queue_name (str): Name of the queue file to be written to AutoLynx (default: 'next.txt').
            do_conversion (bool): If True, initiate post-run data conversion to mzML.
            output_dir (str): Directory to store converted `.mzML` files.

        Returns:
            None
        """
        return await self.hw_device.record_mass_spec(sample_name=sample_name,
                                               run_duration=run_duration,
                                               queue_name=queue_name,
                                               do_conversion=do_conversion,
                                               output_dir=output_dir)