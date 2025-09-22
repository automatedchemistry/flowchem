from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.hamilton.ml600 import ValveType, InvalidConfigurationError
from flowchem.devices.hamilton.ml600_pump import ML600Pump
from flowchem.devices.hamilton.ml600_valve import ML600LeftValve, ML600RightValve
from flowchem.utils.people import samuel_saraiva
from flowchem import ureg
from loguru import logger
import pint


class VirtualML600(FlowchemDevice):
    """Virtual ML600 class to simulate the behavior of the real Hamilton ML600 syringe pump."""

    DEFAULT_CONFIG = {
        "default_infuse_rate": "1 ml/min",
        "default_withdraw_rate": "1 ml/min",
        "valve_left_class": "ML600LeftValve",  # for device with two syringe pump and two valve
        "valve_rigth_class": "ML600RightValve",  # for device with two syringe pump and two valve
        "valve_class": "ML600LeftValve"  # for device with one syringe pump and valve
    }

    def __init__(
        self,
        name: str,
        **config
    ) -> None:
        # Call the parent class constructor with the virtual HamiltonPumpIO
        super().__init__(name)

        # Override device info for virtual device
        self.device_info.authors = [samuel_saraiva]
        self.device_info.manufacturer="Virtual Hamilton"
        self.device_info.model="Virtual ML600"

        self.raw_position = "1"
        self.config = {
            "default_infuse_rate": "1 ml/min",
            "default_withdraw_rate": "1 ml/min",
        }
        self.syringe_volume = ureg.Quantity(config.get("syringe_volume", "10 ml"))
        self._current_volume = self.syringe_volume.magnitude
        self.inspect_valve_argument(config)
        self.dual_syringe = config.get("dual_syringe", "") == "true"

    def inspect_valve_argument(self, config: dict):
        if config.get("valve_left_class") and not config.get("valve_left_class") in ValveType:
            logger.error(f"Invalid valve configuration in left valve of {self.name}! "
                         f"Supported valve types are: {[v.value for v in ValveType]}. Assuming "
                         f"{ML600.DEFAULT_CONFIG['valve_left_class']}!")
            config.pop("valve_left_class")
        if config.get("valve_rigth_class") and not config.get("valve_rigth_class") in ValveType:
            logger.error(f"Invalid valve configuration in rigth valve of {self.name}! "
                         f"Supported valve types are: {[v.value for v in ValveType]}. Assuming "
                         f"{ML600.DEFAULT_CONFIG['valve_rigth_class']}!")
            config.pop("valve_rigth_class")
        if config.get("valve_class") and not config.get("valve_class") in ValveType:
            logger.error(f"Invalid valve configuration in valve of {self.name}! "
                         f"Supported valve types are: {[v.value for v in ValveType]}. Assuming "
                         f"{ML600.DEFAULT_CONFIG['valve_class']}!")
            config.pop("valve_class")
        # This will merger the config into ML600.DEFAULT_CONFIG (in order to update)
        self.config = VirtualML600.DEFAULT_CONFIG | config

    @classmethod
    def from_config(cls, **config):
        config_for_pumpio = {
            k: v
            for k, v in config.items()
            if k not in ("syringe_volume", "address", "name") and k not in cls.DEFAULT_CONFIG
        }
        logger.info(f"Virtual PumpIO ML600 kwargs: {config_for_pumpio}")
        configuration = {
            k: config[k]
            for k in cls.DEFAULT_CONFIG.keys()
            if k in config
        }

        return cls(
            syringe_volume=config.get("syringe_volume", ""),
            address=config.get("address", 1),
            name=config.get("name", ""),
            dual_syringe = config.get("dual_syringe", ""),
            **configuration
        )

    async def initialize(self, hw_init=False, init_speed: str = "200 sec / stroke"):
        """Simulate initializing the virtual ML600 pump."""
        logger.info(f"Virtual ML600 {self.name} with syringe {self.syringe_volume} initialized with conf: {self.config}!")
        # Add device components
        if self.dual_syringe:
            # Add pumps
            self.components.extend([
                ML600Pump("left_pump", self, "B"),
                ML600Pump("right_pump", self, "C")
            ])

            # Handle valve configuration
            left_valve = ValveType(self.config["valve_left_class"])
            right_valve = ValveType(self.config["valve_rigth_class"])
            self.components.extend([
                ML600LeftValve("left_valve", self) if left_valve == ValveType.LEFT else ML600RightValve("left_valve", self),
                ML600RightValve("right_valve", self) if right_valve == ValveType.RIGHT else ML600LeftValve("right_valve", self)
            ])
        else:
            self.components.append(ML600Pump("pump", self))
            valve = ValveType(self.config["valve_class"])
            self.components.append(ML600LeftValve("valve", self) if valve == ValveType.LEFT else ML600RightValve("valve", self))

    async def get_current_volume(self, pump: str) -> pint.Quantity:
        """Return current syringe position in ml."""
        return ureg.Quantity(f"{self._current_volume} ml")  # type: ignore

    async def set_to_volume(self, target_volume: pint.Quantity, rate: pint.Quantity, pump: str):
        """Simulate setting the syringe to a target volume."""
        self._current_volume = target_volume.m_as("ml")  # type: ignore
        logger.info(f"Virtual ML600 {self.name} set to volume {target_volume} at rate {rate}")
        return True

    async def get_pump_status(self, pump: str = "") -> bool:
        """Simulate getting the pump status."""
        return False

    async def get_valve_status(self, valve: str = "") -> bool:
        """Simulate getting the valve status."""
        return True

    async def get_raw_position(self, target_component: str) -> str:
        return self.raw_position

    async def stop(self, pump: str) -> bool:
        """Stop and abort any running command."""
        return True

    async def set_raw_position(
            self,
            target_position: str,
            wait_for_movement_end: bool = True,
            counter_clockwise=False,
            target_component=None
    ):
        self.raw_position = str(target_position)
        logger.debug(f"{self.name} valve position set to position {target_position}, switching CCW")