"""LengthControl Component"""
from loguru import logger
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.devices.flowchem_device import FlowchemDevice


class LengthControl(FlowchemComponent):
    """
    A generic LengthControl component to represent a linear axis system.
    This serves as a base class for components like CNC that deal with positions.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice, mode: str = "discrete", _available_positions: list = [int | float | str]) -> None:
        """
        Initialize the LengthControl component.

        Args:
        name (str): Name of the LengthControl component.
        hw_device (FlowchemDevice): Hardware device interface.
        mode (str): The mode of movement, either "discrete" or "continuous". Default is "discrete".
        _available_positions (list):
            - If mode is "discrete": List of valid positions (float, or str).
            - If mode is "continuous": List containing [min, max] bounds (float or int).
        """
        super().__init__(name, hw_device)
        self.mode = mode.lower()  # discrete or continuous
        if self.mode not in ["discrete", "continuous"]:
            logger.error(f"Invalid mode: {self.mode}. Must be 'discrete' or 'continuous'.")
        if self.mode == "discrete":
            if not all(isinstance(pos, (int, float, str)) for pos in _available_positions):
                logger.error("All positions must be numbers or strings in discrete mode.")
        elif self.mode == "continuous":
            if len(_available_positions) != 2 or _available_positions[0] >= _available_positions[1]:
                logger.error(
                    "In continuous mode, positions must be a list of two values [min, max] "
                    "with min < max."
                )
        self._available_positions = _available_positions

        self.add_api_route("/get_position", self.get_position, methods=["GET"])
        self.add_api_route("/set_position", self.set_position, methods=["PUT"])
        self.add_api_route("/get_available_positions", self.get_available_positions, methods=["GET"])

    async def get_position(self):
        """
        Get the current position of the LengthControl component.

        Returns:
            Union[int, str]: The current position.
        """
        ...

    async def set_position(self, position: int | float | str) -> None:
        """
        Move the LengthControl component to a specific position.

        Args:
            position (Union[float, str]): The desired position to move to.

        """
        def validate_position(axis_name: str, position: int | float | str, mode: str, available_positions: list):
            """Helper function to validate a position for a given axis."""
            if available_positions is None:
                logger.error(f"Available positions for {axis_name}-axis are not set.")

            if mode == "continuous":
                if not isinstance(position, float):
                    logger.error(f"Invalid type for {axis_name}-axis in continuous mode: {position}. Must be a float.")
                if not (available_positions[0] <= position <= available_positions[1]):
                    logger.error(
                        f"{axis_name}-axis position {position} is out of bounds for continuous mode. "
                        f"Bounds: {available_positions[0]} to {available_positions[1]}."
                    )
            elif mode == "discrete":
                if not isinstance(position, (int, float, str)):
                    logger.error(
                        f"Invalid type for {axis_name}-axis in discrete mode: {position}. Must be a float or str."
                    )
                if position not in available_positions:
                    logger.error(
                        f"{axis_name}-axis position {position} is not valid in discrete mode. "
                        f"Available positions: {available_positions}."
                    )

        validate_position(axis_name=self.name, position=position, mode=self.mode, available_positions=self._available_positions)

    async def get_available_positions(self) -> list:
        """
        Get the available positions.

        Returns:
            list:
                - For discrete mode: List of valid positions (float or str).
                - For continuous mode: [min, max] bounds.
        """
        return self._available_positions



