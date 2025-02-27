from time import sleep
from loguru import logger
from flowchem import ureg
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.client.component_client import FlowchemComponentClient

class DualSyringe:
    """
    Autosampler meta components.
    """
    def __init__(self, left_pump=None, right_pump=None, left_valve=None, right_valve=None, syringe_volume: ureg.Quantity | dict[str, ureg.Quantity] | None = None):
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

    def fill_dual_syringes(self, to_volume_left: ureg.Quantity = None, speed_left: ureg.Quantity = None,
                                   to_volume_right: ureg.Quantity = None, speed_right: ureg.Quantity = None):
        """
        Assumes Input on left of valve and output on the right
        """
        if to_volume_right is None and speed_right is None and to_volume_left is not None and speed_left is not None:
            to_volume_right = to_volume_left
            speed_right = speed_left
        # switch valves
        assert self.syringe_volume["left"] == self.syringe_volume[
            "right"], "Syringes are not the same size, this can create unexpected behaviour"
        self.wait_until_idle()
        self.left_valve.put("set_position", {"connect": "[[null,0],[2,3]]"})
        self.right_valve.put("set_position", {"connect": "[[null,0],[2,3]]"})
        #self.wait_until_idle(syringe=None)
        # ToDo Check if it's necessary to get valve's status (is_idle)
        # actuate syringes
        self.left_pump.put("set_to_volume", {"target_volume": str(to_volume_left), "rate": str(speed_left)})
        self.right_pump.put("set_to_volume", {"target_volume": str(to_volume_right), "rate": str(speed_right)})

    def deliver_from_dual_syringes(self, to_volume_left: ureg.Quantity = None, speed_left: ureg.Quantity = None,
                                   to_volume_right: ureg.Quantity = None, speed_right: ureg.Quantity = None):
        """
        Assumes Input on left of valve and output on the right

        Args:
            to_volume:
            speed:

        Returns:

        """
        if to_volume_right is None and speed_right is None and to_volume_left is not None and speed_left is not None:
            to_volume_right = to_volume_left
            speed_right = speed_left
        assert self.syringe_volume["left"] == self.syringe_volume[
            "right"], "Syringes are not the same size, this can create unexpected behaviour"
        # switch valves
        self.wait_until_idle()
        self.left_valve.put("set_position", {"connect": "[[null,null],[2,0]]"})
        self.right_valve.put("set_position", {"connect": "[[null,null],[2,0]]"})
        # self.wait_until_idle(syringe=None)
        # ToDo Check if it's necessary to get valve's status (is_idle)
        # actuate syringes
        self.left_pump.put("set_to_volume", {"target_volume": str(to_volume_left), "rate": str(speed_left)})
        self.right_pump.put("set_to_volume", {"target_volume": str(to_volume_right), "rate": str(speed_right)})

    def fill_single_syringe(self, volume: ureg.Quantity, speed: ureg.Quantity, valve_angle: str ="[[null,1],[null,0]]", syringe="left"):
        """
        Fill a single syringe. This should also work on dual syringe, but only for the left one.
        Assumes Input and output on the right so the valve is not used here


        Args:
            volume:
            speed:

        Returns:

        """
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
                self.left_pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(speed)})
            case "right":
                self.right_valve.put("set_position", {"connect": valve_angle})
                self.wait_until_idle(syringe=syringe)
                curr_vol = self.right_pump.get("get_current_volume")
                to_vol = curr_vol + volume
                to_vol = round(to_vol.m_as("ml"), 3)
                self.right_pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(speed)})
            case _:
                logger.error(f"Invalid syringe value: {syringe}. Expected 'left', 'right', or None.")

    def deliver_from_single_syringe(self, volume_to_deliver: ureg.Quantity, speed: ureg.Quantity , valve_angle: str ="[[null,1],[null,0]]", syringe="left"):
        """
        Assumes Input and output on the right so the valve is not used here

        Args:
            volume_to_deliver:
            speed:
            syringe:

        Returns:

        """
        self.wait_until_idle(syringe=syringe)
        match syringe:
            case "left":
                self.left_valve.put("set_position", {"connect": valve_angle})
                self.wait_until_idle(syringe=syringe)
                curr_vol = self.left_pump.get("get_current_volume")
                to_vol = curr_vol + volume_to_deliver
                to_vol = round(to_vol.m_as("ml"), 3)
                self.left_pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(speed)})
            case "right":
                self.right_valve.put("set_position", {"connect": valve_angle})
                self.wait_until_idle(syringe=syringe)
                curr_vol = self.right_pump.get("get_current_volume")
                to_vol = curr_vol + volume_to_deliver
                to_vol = round(to_vol.m_as("ml"), 3)
                self.right_pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(speed)})
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



