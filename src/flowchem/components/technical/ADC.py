from __future__ import annotations

from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class AnalogDigitalSignal(FlowchemComponent):
    """
    Component representing an analog/digital signal in a Flowchem device.

    This component provides a simple API route (`/read`) to obtain the current
    value of a signal, abstracting the details of the underlying hardware.
    It is semantically linked to the SOSA ontology as an `Observation`, i.e.
    an act of estimating or calculating a value of a property of a
    `FeatureOfInterest` using a `Sensor`.

    Attributes:
        component_info (ComponentInfo): Metadata about the component,
            extended with the SOSA ontology subclass `Observation`.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device)
        self.add_api_route("/read", self.read, methods=["GET"])

        # Ontology: Act of carrying out an (Observation)
        # Procedure to estimate or calculate a value of a property of a
        # FeatureOfInterest. Links to a Sensor to describe what made the
        # Observation and how;
        self.component_info.owl_subclass_of.append(
            "http://www.w3.org/ns/sosa/Observation",
        )

    async def read(self, **kwargs) -> float:
        """
        Read the current value of the signal.

        Args:
            **kwargs: Additional keyword arguments for future extension.

        Returns:
            float: The measured or estimated signal value.
                   Currently a placeholder (`0.0`).
        """
        return 0.0


