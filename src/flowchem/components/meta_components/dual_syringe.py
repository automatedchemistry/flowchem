from time import sleep
from loguru import logger
from flowchem import ureg
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.client.component_client import FlowchemComponentClient


class DualSyringe:
    """
    Dual syringe pump meta components.
    """
    def __init__(self, left_pump=None, right_pump=None, left_valve=None, right_valve=None,
                 syringe_volume: ureg.Quantity | dict[str, ureg.Quantity] | None = None):
        self.left_pump: FlowchemComponentClient = left_pump
        self.right_pump: FlowchemComponentClient = right_pump
        self.left_valve: FlowchemComponentClient = left_valve
        self.right_valve: FlowchemComponentClient = right_valve
        if type(syringe_volume) is ureg.Quantity:
            self.syringe_volumes = {"left": syringe_volume, "right": syringe_volume}
        elif isinstance(syringe_volume, dict) and all(isinstance(key, ureg.Quantity) for key in syringe_volume.keys()):
            self.syringe_volume = {"left": syringe_volume["left"], "right": syringe_volume["right"]}
        else:
            raise InvalidConfigurationError("Please provide valid syringe volumes as a single str (ex: '5 ml') or a dict"
                                            "  ({'left': '5 ml', 'right': '1 ml'})")

    def fill_dual_syringes(self, to_volume_left: ureg.Quantity = None, flowrate_left: ureg.Quantity = None,
                                   to_volume_right: ureg.Quantity = None, flowrate_right: ureg.Quantity = None):
        """
        Assumes Input on left of valve and output on the right
        """
        if not flowrate_left.check("[volume] / [time]") | flowrate_right.check("[volume] / [time]"):
            raise ValueError("Flowrate must be a quantity with units of volume per time (e.g., 'ml/min').")
        if not to_volume_left.check("[volume]") | to_volume_right.check("[volume]"):
            raise ValueError("Volume must be a quantity with units of volume (e.g., 'ml').")
        if to_volume_right is None and flowrate_right is None and to_volume_left is not None and flowrate_left is not None:
            to_volume_right = to_volume_left
            flowrate_right = flowrate_left
        # switch valves
        assert self.syringe_volume["left"] == self.syringe_volume[
            "right"], "Syringes are not the same size, this can create unexpected behaviour"
        self.wait_until_idle()
        self.left_valve.put("set_position", {"connect": "[[null,0],[2,3]]"})
        self.right_valve.put("set_position", {"connect": "[[null,0],[2,3]]"})
        #self.wait_until_idle(syringe=None)
        # ToDo Check if it's necessary to get valve's status (is_idle)
        # actuate syringes
        self.left_pump.put("set_to_volume", {"target_volume": str(to_volume_left), "rate": str(flowrate_left)})
        self.right_pump.put("set_to_volume", {"target_volume": str(to_volume_right), "rate": str(flowrate_right)})

    def deliver_from_dual_syringes(self, to_volume_left: ureg.Quantity = None, flowrate_left: ureg.Quantity = None,
                                   to_volume_right: ureg.Quantity = None, flowrate_right: ureg.Quantity = None):
        """
        Assumes Input on left of valve and output on the right

        Args:
            to_volume:
            speed:

        Returns:

        """
        if not flowrate_left.check("[volume] / [time]") | flowrate_right.check("[volume] / [time]"):
            raise ValueError("Flowrate must be a quantity with units of volume per time (e.g., 'ml/min').")
        if not to_volume_left.check("[volume]") | to_volume_right.check("[volume]"):
            raise ValueError("Volume must be a quantity with units of volume (e.g., 'ml').")
        if to_volume_right is None and flowrate_right is None and to_volume_left is not None and flowrate_left is not None:
            to_volume_right = to_volume_left
            speed_right = flowrate_left
        assert self.syringe_volume["left"] == self.syringe_volume[
            "right"], "Syringes are not the same size, this can create unexpected behaviour"
        # switch valves
        self.wait_until_idle()
        self.left_valve.put("set_position", {"connect": "[[null,null],[2,0]]"})
        self.right_valve.put("set_position", {"connect": "[[null,null],[2,0]]"})
        # self.wait_until_idle(syringe=None)
        # ToDo Check if it's necessary to get valve's status (is_idle)
        # actuate syringes
        self.left_pump.put("set_to_volume", {"target_volume": str(to_volume_left), "rate": str(flowrate_left)})
        self.right_pump.put("set_to_volume", {"target_volume": str(to_volume_right), "rate": str(flowrate_right)})

    def fill_single_syringe(self, volume: ureg.Quantity, flowrate: ureg.Quantity, valve_angle: str ="[[null,1],[null,0]]", syringe="left"):
        """
        Fill a single syringe. This should also work on dual syringe, but only for the left one.
        Assumes Input and output on the right so the valve is not used here


        Args:
            volume:
            speed:

        Returns:

        """
        if not flowrate.check("[volume] / [time]"):
            raise ValueError("Flowrate must be a quantity with units of volume per time (e.g., 'ml/min').")
        if not volume.check("[volume]"):
            raise ValueError("Volume must be a quantity with units of volume (e.g., 'ml').")
        # switch valves
        assert syringe in ["left", "right"], "Either select left or right syringe"
        self.wait_until_idle(syringe=syringe)
        # easy to get working on right one: just make default variable for right or left
        match syringe:
            case "left":
                self.left_valve.put("set_position", {"connect": valve_angle})
                self.wait_until_idle(syringe=syringe)
                curr_vol = self.left_pump.get("get_current_volume")
                to_vol = curr_vol + volume
                to_vol = round(to_vol.m_as("ml"),3)
                self.left_pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(flowrate)})
            case "right":
                self.right_valve.put("set_position", {"connect": valve_angle})
                self.wait_until_idle(syringe=syringe)
                curr_vol = self.right_pump.get("get_current_volume")
                to_vol = curr_vol + volume
                to_vol = round(to_vol.m_as("ml"), 3)
                self.right_pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(flowrate)})
            case _:
                logger.error(f"Invalid syringe value: {syringe}. Expected 'left', 'right', or None.")

    def deliver_from_single_syringe(self, volume_to_deliver: ureg.Quantity, flowrate: ureg.Quantity , valve_angle: str ="[[null,1],[null,0]]", syringe="left"):
        """
        Assumes Input and output on the right so the valve is not used here

        Args:
            volume_to_deliver:
            speed:
            syringe:

        Returns:

        """
        # Check if desired units
        if not flowrate.check("[volume] / [time]"):
            raise ValueError("Flowrate must be a quantity with units of volume per time (e.g., 'ml/min').")
        if not volume_to_deliver.check("[volume]"):
            raise ValueError("Volume must be a quantity with units of volume (e.g., 'ml').")
        self.wait_until_idle(syringe=syringe)
        match syringe:
            case "left":
                self.left_valve.put("set_position", {"connect": valve_angle})
                self.wait_until_idle(syringe=syringe)
                curr_vol = self.left_pump.get("get_current_volume")
                to_vol = curr_vol + volume_to_deliver
                to_vol = round(to_vol.m_as("ml"), 3)
                self.left_pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(flowrate)})
            case "right":
                self.right_valve.put("set_position", {"connect": valve_angle})
                self.wait_until_idle(syringe=syringe)
                curr_vol = self.right_pump.get("get_current_volume")
                to_vol = curr_vol + volume_to_deliver
                to_vol = round(to_vol.m_as("ml"), 3)
                self.right_pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(flowrate)})
            case _:
                logger.error(f"Invalid syringe value: {syringe}. Expected 'left', 'right', or None.")

    def wait_until_idle(self, syringe=None):
        """ Waits for both pumps to be idle. """
        match syringe:
            case None:
                logger.debug(f"wait until both pumps idle")
                while self.left_pump.get("is_pumping") or self.right_pump.get("is_pumping"):
                    sleep(0.001)
            case "left":
                logger.debug(f"wait until left pump idle")
                while self.left_pump.get("is_pumping"):
                    sleep(0.001)
            case "right":
                logger.debug(f"wait until right pump idle")
                while self.right_pump.get("is_pumping"):
                    sleep(0.001)
            case _:
                logger.error(f"Invalid syringe value: {syringe}. Expected 'left', 'right', or None.")

    def home_syringe(self, syringe="left",
                     flowrate_left: ureg.Quantity | None = None,
                     flowrate_right: ureg.Quantity | None = None,
                     connect_left="[[null,1],[null,0]]",
                     connect_right="[[null,1],[null,0]]"):
        """
        Homes syringes. Default for ML600 syringes
        """
        # Defaults to twice the volume in ml/min
        if not flowrate_left and (syringe == "left" or syringe is None):
            flowrate_left = ureg.Quantity(f"{self.syringe_volume["left"].m_as("ml") * 2} ml/min")
        if not flowrate_right and (syringe == "right" or syringe is None):
            flowrate_right = ureg.Quantity(f"{self.syringe_volume["right"].m_as("ml") * 2} ml/min")
        # Checks for unit
        if flowrate_left and not flowrate_left.check("[volume] / [time]") or flowrate_right and not flowrate_right.check("[volume] / [time]"):
            raise ValueError("Flowrate must be a quantity with units of volume per time (e.g., 'ml/min').")
        if syringe == "left" or syringe is None:
            self.left_pump.get("wait_until_idle")
            self.left_valve.put("set_position", {"connect": connect_left})
            self.left_pump.get("wait_until_idle")
            self.left_pump.put("set_to_volume", {"volume": "0 ml", "rate": f"{flowrate_left} ml/min"})
            if syringe == "right" or syringe is None:
                self.right_pump.get("wait_until_idle")
                self.right_valve.put("set_position", {"connect": connect_right})
                self.right_pump.get("wait_until_idle")
                self.right_pump.put("set_to_volume", {"volume": "0 ml", "rate": f"{flowrate_right} ml/min"})
            else:
                logger.error(f"Invalid syringe value: {syringe}. Expected 'left', 'right', or None for both.")



