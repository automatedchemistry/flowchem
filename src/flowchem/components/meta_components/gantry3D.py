"""Base gantry3D meta component."""
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.technical.length import LengthControl
from flowchem.devices.flowchem_device import FlowchemDevice


class gantry3D(FlowchemComponent):
    """
    A gantry3D device that controls movement in 3 dimensions (X, Y, Z).
    Each axis can operate in discrete or continuous mode.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice, axes_config: dict) -> None:
        """
        Initialize the gantry3D component with individual LenghtControl components for X, Y, and Z axes.

        Args:
            name (str): Name of the gantry3D device.
            hw_device (FlowchemDevice): Hardware device interface.
            axes_config (dict): Configuration for each axis. Example:
                {
                    "x": {"mode": "discrete", "positions": [0, 10, 20]},
                    "y": {"mode": "continuous", "positions": [0.0, 100.0]},
                    "z": {"mode": "discrete", "positions": ["A", "B", "C"]}
                }
        """
        super().__init__(name, hw_device)
        self.add_api_route("/set_x_position", self.set_x_position, methods=["PUT"])
        self.add_api_route("/set_y_position", self.set_y_position, methods=["PUT"])
        self.add_api_route("/set_z_position", self.set_z_position, methods=["PUT"])

        self.x_axis = LengthControl(
            f"{name}_x",
            hw_device,
            mode=axes_config["x"]["mode"],
            _available_positions=axes_config["x"]["positions"],
        )
        self.y_axis = LengthControl(
            f"{name}_y",
            hw_device,
            mode=axes_config["y"]["mode"],
            _available_positions=axes_config["y"]["positions"],
        )
        self.z_axis = LengthControl(
            f"{name}_z",
            hw_device,
            mode=axes_config["z"]["mode"],
            _available_positions=axes_config["z"]["positions"],
        )

    async def set_x_position(self, position: int | float | str) -> None:
        """
        Set the position of the X-axis.

        Args:
            position (float | str): Target position for the X-axis.
        """
        if isinstance(position, str) and position.isnumeric():
            position = float(position) if "." in position else int(position)
        await self.x_axis.set_position(position)

    async def set_y_position(self, position: int | float | str) -> None:
        """
        Set the position of the Y-axis.

        Args:
            position (float | str): Target position for the Y-axis.
        """
        if isinstance(position, str) and position.isnumeric():
            position = float(position) if "." in position else int(position)
        await self.y_axis.set_position(position)

    async def set_z_position(self, position: int | float | str) -> bool:
        """
        Set the position of the Z-axis.

        Args:
            position (float | str): Target position for the Z-axis.
        """
        if isinstance(position, str) and position.isnumeric():
            position = float(position) if "." in position else int(position)
        await self.z_axis.set_position(position)
        return True


