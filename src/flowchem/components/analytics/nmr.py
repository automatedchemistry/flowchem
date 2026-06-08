"""An NMR control component."""

from fastapi import BackgroundTasks

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class NMRControl(FlowchemComponent):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """NMR Control component."""
        super().__init__(name, hw_device)
        self.add_api_route("/acquire-spectrum", self.acquire_spectrum, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])

        # Ontology: fourier transformation NMR instrument
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/OBI_0000487",
        )
        self.component_info.type = "NMR Control"

    async def acquire_spectrum(self, background_tasks: BackgroundTasks):
        """Acquire an NMR spectrum."""
        ...

    async def stop(self):
        """Stop acquisition and exit gracefully."""
        ...
