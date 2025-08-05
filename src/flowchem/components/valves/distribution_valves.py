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
                         rotor_ports=[(5, None, None, None), (5,)],
                         )


class SixPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(1, 2, 3, 4, 5, 6), (0,)],
            rotor_ports=[(7, None, None, None, None, None), (7,)],
        )

class EightPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(1, 2, 3, 4, 5, 6, 7, 8), (0,)],
            rotor_ports=[(9, None, None, None, None, None, None, None), (9,)],
        )


class TenPortDistributionValve(Valve):
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(1, 2, 3, 4, 5, 6, 7, 8, 9, 10), (0,)],
            rotor_ports=[(11, None, None, None, None, None, None, None, None, None), (11,)],
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


# tot this should be 4 port sth valve
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


# tot this should be 4 port
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


class FourPortFivePositionValve(Valve):
    """
    This is of type HamiltonDualPumpValveOnLeft
    """
    # rotor and stator look confusing, however this is necessary to apply the logic
    def __init__(self, name: str, hw_device: FlowchemDevice) -> None:
        super().__init__(
            name,
            hw_device,
            stator_ports=[(None, None, 1, None, 2, None, 3, None,), (0,)],
            rotor_ports=[(None, 5, None, None, 4, None, 4, None), (5,)],
        )

