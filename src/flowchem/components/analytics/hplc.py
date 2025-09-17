"""An HPLC control component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class HPLCControl(FlowchemComponent):
    """
    A component for controlling an HPLC (High Performance Liquid Chromatography) system.

    Attributes:
    -----------
    hw_device : FlowchemDevice
        The hardware device (HPLC) this component interfaces with.

    Methods:
    --------
    send_method(method_name: str):
        Submit a method to the HPLC system. This is useful when automatic actions, like switching a valve, are triggered.
    run_sample(sample_name: str, method_name: str):
        Run an HPLC sample using the specified sample and method.
    """
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """
        Constructs all the necessary attributes for the HPLCControl object.

        Parameters:
        -----------
        name : str
            The name of the HPLC control component.
        hw_device : FlowchemDevice
            The hardware device (HPLC) this component interfaces with.
        """
        super().__init__(name, hw_device)
        self.add_api_route("/run-sample", self.run_sample, methods=["PUT"])
        self.add_api_route("/send-method", self.send_method, methods=["PUT"])

        # Ontology: high performance liquid chromatography instrument
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/OBI_0001057",
        )
        self.component_info.type = "HPLC Control"

    async def send_method(self, method_name):
        """
        Set or load a analytical method to the HPLC system.

        This method is useful for scenarios where an injection is automatically triggered, such as when switching a valve.

        Note that the commands is wrapped in the run sample

        Parameters:
        -----------
        method_name : str
            The name of the method to be submitted.

        Returns:
        --------
        None
        """
        ...

    async def run_sample(self, sample_name: str, method_name: str):
        """
        Run an HPLC sample using the provided sample name and method.

        Parameters:
        -----------
        sample_name : str
            The name of the sample to run.
        method_name : str
            The name of the method to use for running the sample.

        Returns:
        --------
        None
        """
        ...
