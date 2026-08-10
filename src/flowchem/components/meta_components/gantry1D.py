"""Base marker component for devices that physically move to a position."""

from flowchem.components.flowchem_component import FlowchemComponent


class Gantry(FlowchemComponent):
    """Shared root for gantry-style movement components.

    Represents a single degree of freedom (one axis). Adds no behavior of
    its own — it exists purely so devices that move to a position
    (single-axis fraction collectors, multi-axis autosampler gantries via
    Gantry3D, future linear/XY stages, ...) share an MRO node, visible in
    ComponentInfo.corresponding_class and usable via
    isinstance(component, Gantry), regardless of axis count or how
    position is represented by the concrete hardware.
    """
