"""An MS control component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.flowchem_component import FlowchemComponent

if TYPE_CHECKING:
    from flowchem.devices.flowchem_device import FlowchemDevice


class MSControl(FlowchemComponent):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """MS Control component. Sends methods and starts run."""
        super().__init__(name, hw_device)
        self.add_api_route("/run-sample", self.run_sample, methods=["PUT"])
        self.add_api_route("/send-method", self.send_method, methods=["PUT"])

        # Ontology: A mass spectrometer is an instrument which is used to measure the mass to charge ratio of ions
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/OBI_0000049",
        )
        self.component_info.type = "Mass Spectrometer Control"

    async def run_sample(self, sample_name: str):
        """Run MS sample with the provided sample name and method."""
        ...

    async def send_method(self, method_name):
        """
        Submit method to MS.
        """
        ...