"""Distribution valves, generally connected to syringe pumps, direct the flow from a fixed port to one of the others."""
from flowchem.components.valves.valve import Valve
from flowchem.devices.flowchem_device import FlowchemDevice


class TwoPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device,
                         stator_ports=[(1, 2), (0,)],
                         rotor_ports=[(3, None), (3,)],
                         )


class FourPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(name, hw_device,
                         stator_ports=[(1, 2, 3, 4), (0,)],
                         rotor_ports=[(3, None, None, None), (3,)],
                         )


class SixPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(1, 2, 3, 4, 5, 6), (0,)],
            rotor_ports=[(7, None, None, None, None, None), (7,)],
        )


class TwelvePortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12), (0,)],
            rotor_ports=[(13, None, None, None, None, None, None, None, None, None, None, None), (13,)],
        )


class SixteenPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16), (0,)],
            rotor_ports=[(17, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None),
                         (17,)],
        )


class ThreePortFourPositionValve(Valve):
    """
    This is of type HamiltonDualPumpValveOnRight
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(None, 1, 2, 3,), (0,)],
            rotor_ports=[(4, 4, 5, 5), (4,)],
        )


class ThreePortTwoPositionValve(Valve):
    """
    This is of type HamiltonDualPumpValveOnLeft
    """

    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(None, 1, 2, 3,), (0,)],
            rotor_ports=[(4, 4, None, None), (None,)],
        )
