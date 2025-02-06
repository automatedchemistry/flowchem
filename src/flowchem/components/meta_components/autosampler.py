"""Base Autosampler meta component."""
from loguru import logger
from time import sleep
import json
from flowchem.components.flowchem_component import FlowchemComponent
from flowchem.components.meta_components.gantry3D import gantry3D
from flowchem.components.pumps.syringe_pump import SyringePump
from flowchem.components.valves.valve import ValveInfo, return_tuple_from_input
from flowchem.components.valves.distribution_valves import (
    TwoPortDistributionValve,
    FourPortDistributionValve,
    SixPortDistributionValve,
    TwelvePortDistributionValve,
    SixteenPortDistributionValve,
    )
from flowchem.components.valves.injection_valves import SixPortTwoPositionValve
from flowchem.devices.flowchem_device import FlowchemDevice


class ASInjectionValve(SixPortTwoPositionValve):

    def __init__(self, name: str, hw_device: FlowchemDevice, mapping: dict = None):
        self.identifier = "injection_valve"
        self.mapping = mapping
        super().__init__(name, hw_device)

class ASSyringeValve(FourPortDistributionValve):

    def __init__(self, name: str, hw_device: FlowchemDevice, mapping: dict = None):
        self.identifier = "syringe_valve"
        self.mapping = mapping
        super().__init__(name, hw_device)

class Autosampler(FlowchemComponent):
    """
    A CNC device that controls movement in 3 dimensions (X, Y, Z).
    Each axis can operate in discrete or continuous mode.
    """

    def __init__(self, name: str, hw_device: FlowchemDevice, _config: dict) -> None:
        """
        Initialize the Autosampler component with individual components.

        Args:
            name (str): Name of the CNC device.
            hw_device (FlowchemDevice): Hardware device interface.
            axes_config (dict): Configuration for each axis. Example:
                _config = {
                    "tray_config": {
                        "rows": [1, 2, 3, 4, 5, 6, 7, 8],
                        "columns": ["a", "b", "c", "d", "e", "f"]
                    },
                    "needle_positions": ["WASH", "WASTE", "EXCHANGE", "TRANSPORT"],
                    "syringe_valve": {"mapping": {0: "NEEDLE", 1: "WASH",  2: "WASH_PORT2", 3: "WASTE"},
                }
        """
        super().__init__(name, hw_device)
        self._config = _config

        #gantry3D
        self.add_api_route("/needle_position", self.set_needle_position, methods=["PUT"])
        self.add_api_route("/set_xy_position", self.set_xy_position, methods=["PUT"])
        self.add_api_route("/set_z_position", self.set_z_position, methods=["PUT"])
        self.add_api_route("/connect_to_position", self.connect_to_position, methods=["PUT"])
        self.add_api_route("/is_needle_running", self.is_needle_running, methods=["GET"])
        #Pump
        self.add_api_route("/infuse", self.infuse, methods=["PUT"])
        self.add_api_route("/withdraw", self.withdraw, methods=["PUT"])
        self.add_api_route("/is_pumping", self.is_pumping, methods=["GET"])
        #Syringe Valve
        self.add_api_route("/syringe_valve_position", self.set_syringe_valve_position, methods=["PUT"])
        self.add_api_route("/syringe_valve_position_monitor", self.set_syringe_valve_position_monitor, methods=["PUT"])
        self.add_api_route("/syringe_valve_position", self.get_syringe_valve_position, methods=["GET"])
        self.add_api_route("/syringe_valve_connections", self.syringe_valve_connections, methods=["GET"])
        #Injection Valve
        self.add_api_route("/injection_valve_position", self.set_injection_valve_position, methods=["PUT"])
        self.add_api_route("/injection_valve_position_monitor", self.set_injection_valve_position_monitor, methods=["PUT"])
        self.add_api_route("/injection_valve_position", self.get_injection_valve_position, methods=["GET"])
        self.add_api_route("/injection_valve_connections", self.injection_valve_connections, methods=["GET"])

        #Meta Methods
        self.add_api_route("/wash_needle", self.wash_needle, methods=["PUT"])
        #self.add_api_route("/fill_wash_reservoir", self.fill_wash_reservoir, methods=["PUT"])
        #self.add_api_route("/empty_wash_reservoir", self.empty_wash_reservoir, methods=["PUT"])
        self.add_api_route("/pick_up_sample", self.pick_up_sample, methods=["PUT"])

        # valve_class_map = {
        #     "FourPortDistributionValve": FourPortDistributionValve,
        #     "SixPortDistributionValve": SixPortDistributionValve,
        # }
        _config["axes_config"] = {
            "x": {"mode": "discrete", "positions": _config["tray_config"]["rows"]},
            "y": {"mode": "discrete", "positions": _config["tray_config"]["columns"]},
            "z": {"mode": "discrete", "positions": ["UP", "DOWN"]}
        }

        # Check config #
        #Syringe valve mapping
        required_syringe_valve_values = {"NEEDLE", "WASH", "WASTE"}  # Set of required values
        syringe_mapping = _config.get("syringe_valve", {}).get("mapping", {})
        updated_mapping = {key: value.upper() for key, value in syringe_mapping.items()}
        missing_values = required_syringe_valve_values - set(updated_mapping.values())  # Check if required values are in the mapping
        if missing_values:
            logger.error(f"Missing required values in syringe valve mapping: {missing_values}")
        _config["syringe_valve"]["mapping"] = updated_mapping
        #Needle positions
        required_needle_positions = {"WASH", "WASTE"}
        needle_positions = _config.get("needle_positions", [])
        updated_needle_positions = [pos.upper() for pos in needle_positions]
        missing_needle_positions = required_needle_positions - set(updated_needle_positions)
        if missing_needle_positions:
            logger.error(f"Missing required needle positions: {missing_needle_positions}")
        _config["needle_positions"] = updated_needle_positions


        self.gantry3D = gantry3D(
            f"{name}_gantry3D",
            hw_device,
            axes_config=_config["axes_config"],
        )
        self.pump = SyringePump(
            f"{name}_pump",
            hw_device,
        )
        # valve_type = _config["syringe_valve"]["type"]
        # if valve_type not in valve_class_map:
        #     logger.error(
        #         f"Invalid syringe_valve_type: {valve_type}. "
        #         f"Must be one of {list(valve_class_map.keys())}."
        #     )
        #ToDo: Is the syringe valve always four ports?
        self.syringe_valve = ASSyringeValve(
            f"{name}_syringe_valve",
            hw_device,
            _config["syringe_valve"]["mapping"]
        )
        #self.syringe_valve.identifier = "syringe_valve"
        #self.syringe_valve.mapping = _config["syringe_valve"]["mapping"]

        self.injection_valve = ASInjectionValve(
                f"{name}_injection_valve",
                hw_device,
            {0: "LOAD", 1: "INJECT"}
            )
        #self.injection_valve.identifier = "injection_valve"
        #self.injection_valve.mapping = {0: 'LOAD', 1: 'INJECT'}

    # Gantry3D Methods
    async def is_needle_running(self) -> bool:
        """"Checks if needle is running"""
    ...

    async def set_needle_position(self, position: str = "") -> None:
        """
        Move the needle to one of the predefined positions.
        """
        if position not in self._config["needle_positions"]:
            logger.error(
                f"Invalid needle position: '{position}'. "
                f"Must be one of {self._config['needle_positions']}."
            )

    # async def get_needle_position(self) -> dict:
    #     """
    #     Get.
    #     """
    #     pos = await self.gantry3D.get_position()
    #     return pos

    async def connect_to_position(self, row: int | float | str = "", column: int | float | str = "" ):
            await self.set_xy_position(x=row,y=column)
            await self.gantry3D.set_z_position("DOWN")
            return True


    async def set_xy_position(self, x: int | float | str = 0, y: int | float | str = 0) -> None:
        """
        Move the 3D gantry to the specified (x, y) coordinate.
        """
        await self.gantry3D.set_x_position(position=x)
        await self.gantry3D.set_y_position(position=y)
    # Necessary to return values? Maybe just call super().set_xy_position() to run checks before the actual set_xy_position() from the autosampler.

    async def set_z_position(self, z: int | float | str = 0) -> None:
        """
        Move the 3D gantry to the specified (x, y) coordinate.
        """
        await self.gantry3D.set_z_position(position=z)

    # Pump Methods
    async def infuse(self, rate: str = None, volume: str = None) -> bool:
        """
        Dispense with syringe.
        Args:
            volume: volume to dispense in mL

        Returns: None
        """
        success = await self.pump.infuse(rate=rate, volume=volume)
        return success

    async def withdraw(self, rate: str = None, volume: str = None) -> bool:  # type: ignore
        """
        Aspirate with built in syringe.
        Args:
            volume: volume to aspirate in mL

        Returns: None
        """
        success = await self.pump.withdraw(rate=rate, volume=volume)
        return success

    async def is_pumping(self) -> bool:
        status = await self.pump.is_pumping()
        return status

    async def wait_for_syringe(self):
        while True:
            if not await self.is_pumping():
                break
            else:
                sleep(0.01)

    async def wait_until_ready(self, wait_for_syringe=True):
        """
        Wait for AS to be done
        Args:
            wait_for_syringe: If True (default), also the external syringe will be waited for.
                            If False it can run in background

        Returns: None

        """
        while True:
            if not await self.is_needle_running():
                # if theres external syringe, wait for it to get ready
                if wait_for_syringe == True:
                    if not await self.is_pumping():
                        break
                else:
                    break
            sleep(0.01)

    # Syringe valve Methods
    async def set_syringe_valve_position(self, position: str = None):
        """Write the connections to make in the syringe valve.
            Example: "[[1,0]]"
        """
        await self.syringe_valve.set_position(connect=position)
        current_pos = await self.get_syringe_valve_position()
        logger.debug(f"current_pos {current_pos}")
        logger.debug(f"position {position}")
        if current_pos == return_tuple_from_input(position):
            return True

    async def get_syringe_valve_position(self) -> list[list[int | None]]:
        """Retrieve the current connections of the syringe valve."""
        return await self.syringe_valve.get_position()

    async def set_syringe_valve_position_monitor(self, position: str = None) -> bool:
        """Select which position you want to set on the syringe valve according to mapping.
        Example: "WASH"
        """
        pos_num = self.syringe_valve._change_connections(raw_position=position, reverse=True)
        pos_str = json.dumps(list(self.syringe_valve._positions.get(int(pos_num))))
        await self.set_syringe_valve_position(position=pos_str)
        return True

    async def set_injection_valve_position_monitor(self, position: str = None) -> bool:
        pos_num = self.injection_valve._change_connections(raw_position=position, reverse=True)
        pos_str = json.dumps(list(self.injection_valve._positions.get(int(pos_num))))
        await self.set_injection_valve_position(position=pos_str)
        return True

    def syringe_valve_connections(self) -> ValveInfo:
        """Get the list of all available positions for this valve.
                This mainly has informative purpose
                """
        return self.syringe_valve.connections()

    # Injection valve Methods
    async def set_injection_valve_position(self, position: str = None):
        """Set the position of the injection valve."""
        await self.injection_valve.set_position(connect=position)
        current_pos = await self.get_injection_valve_position()
        logger.debug(f"current_pos {current_pos}")
        logger.debug(f"position {position}")
        if current_pos == return_tuple_from_input(position):
            return True

    async def get_injection_valve_position(self) -> list[list[int | None]]:
        """Retrieve the current position of the injection valve."""
        return await self.injection_valve.get_position()

    def injection_valve_connections(self) -> ValveInfo:
        """Get the list of all available positions for this valve.
        This mainly has informative purpose
        """
        return self.injection_valve.connections()

    # AS Methods
    async def fill_wash_reservoir(self, volume: str = "0.2 ml", rate: str = None):
        """
        Fill the wash reservoir with a specified volume and rate.

        Args:
            volume (float): Volume to be used for filling the wash reservoir. Default is 0.2 mL.
            rate (float): Flow rate for filling the reservoir. If not provided, the default rate is used.
        """
        await self.set_syringe_valve_position_monitor("WASH")
        await self.withdraw(rate=rate, volume=volume)
        await self.set_needle_position("WASH")
        await self.set_z_position("DOWN")
        await self.wait_until_ready()
        await self.set_injection_valve_position_monitor("LOAD")
        await self.wait_until_ready()
        await self.set_syringe_valve_position_monitor("NEEDLE")
        await self.wait_until_ready()
        await self.infuse(rate=rate, volume=volume)
        await self.wait_for_syringe()
        await self.set_z_position("UP")

    async def empty_wash_reservoir(self, volume: str = "0.2 ml", rate: str = None):
        """
        Empty the wash reservoir by withdrawing a specified volume.

        Args:
            volume (float): Volume to be removed from the wash reservoir. Default is 0.2 mL.
            rate (float): Flow rate for emptying the reservoir. If not provided, the default rate is used.
        """
        await self.set_needle_position("WASH")
        await self.set_z_position("DOWN")
        await self.pick_up_sample(rate=rate, volume=volume)
        await self.set_z_position("UP")

    async def pick_up_sample(self, volume: str = "0 ml", rate: str = None):
        """
        Pick up a sample using the syringe.

        Args:
            volume (float): Volume of the sample to pick up. Default is 0.2 mL.
            rate (float): Flow rate for withdrawing the sample. If not provided, the default rate is used.
        """
        await self.set_injection_valve_position_monitor("LOAD")
        await self.wait_until_ready()
        await self.set_syringe_valve_position_monitor("NEEDLE")
        await self.withdraw(rate=rate, volume=volume)
        await self.wait_until_ready()

    async def wash_needle(self, volume: str = "0.2 ml", times: int = 1, rate: str = None) -> bool:
        """
        Fill needle with solvent and then wash it.
        """
        for i in range(times):
            await self.fill_wash_reservoir(volume=volume, rate=rate)
            await self.empty_wash_reservoir(volume=volume, rate=rate)
            await self.set_needle_position("WASTE")
            await self.set_z_position("DOWN")
            # dispense to waste and go up
            await self.infuse(rate=rate, volume=volume)
            await self.wait_until_ready()
            await self.set_z_position("UP")
        return True
