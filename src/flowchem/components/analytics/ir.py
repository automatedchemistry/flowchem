"""An IR control component."""

from pydantic import BaseModel

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class IRSpectrum(BaseModel):
    """IR spectrum class.

    Consider rampy for advance features (baseline fit, etc.)
    See e.g. https://github.com/charlesll/rampy/blob/master/examples/baseline_fit.ipynb
    """

    wavenumber: list[float]
    intensity: list[float]


class IRControl(FlowchemComponent):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        """HPLC Control component. Sends methods, starts run, do stuff."""
        super().__init__(name, hw_device)
        self.add_api_route("/acquire-spectrum", self.acquire_spectrum, methods=["PUT"])
        self.add_api_route("/stop", self.stop, methods=["PUT"])

        # Ontology: high performance liquid chromatography instrument
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/OBI_0001057",
        )
        self.component_info.type = "IR Control"

    async def acquire_spectrum(self) -> IRSpectrum:  # type: ignore
        """Acquire an IR spectrum."""
        ...

    async def stop(self):
        """Stop acquisition and exit gracefully."""
        ...
