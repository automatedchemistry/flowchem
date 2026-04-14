"""Injection valves are multiport, two-position valves, e.g. 6-2 commonly used w/ injection loops for HPLC injection."""

from flowchem.components.valves.valve import Valve
from flowchem.devices.flowchem_device import FlowchemDevice


class SixPortTwoPositionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        # These are hardware-port, only input and output are routable from the fixed syringe.
        # All three are listed as this simplifies the creation of graphs
        super().__init__(
            name,
            hw_device,
            stator_ports=[(1, 2, 3, 4, 5, 6), ()],
            rotor_ports=[(7, 7, 8, 8, 9, 9), ()],
        )
