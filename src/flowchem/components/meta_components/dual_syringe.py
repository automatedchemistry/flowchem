from time import sleep
from flowchem import ureg
from flowchem.utils.exceptions import InvalidConfigurationError
from flowchem.client.component_client import FlowchemComponentClient


class DualSyringe:
    """
    Autosampler meta components.
    """
    def __init__(self, left_pump=None, right_pump=None, left_valve=None, right_valve=None, syringe_volumes: dict | str | None = None):
        self.left_pump: FlowchemComponentClient = left_pump
        self.right_pump: FlowchemComponentClient = right_pump
        self.left_valve: FlowchemComponentClient = left_valve
        self.right_valve: FlowchemComponentClient = right_valve
        if type(syringe_volumes) is str:
            self.syringe_volumes = {"left": ureg.Quantity(syringe_volumes), "right": syringe_volumes}
        elif isinstance(syringe_volumes, dict) and all(isinstance(key, str) for key in syringe_volumes.keys()):
            self.syringe_volumes = {"left": syringe_volumes["left"], "right": syringe_volumes["right"]}
        else:
            raise InvalidConfigurationError("Please provide valid syringe volumes as a single str (ex: '5 ml') or a dict"
                                            "  ({'left': '5 ml', 'right': '1 ml'})")

    def fill_dual_syringes(self, to_volume_left: float = None, speed_left: float = None,
                                   to_volume_right: float = None, speed_right: float = None):
        """
        Assumes Input on left of valve and output on the right
        """
        # switch valves
        assert self.syringe_volumes["left"] == self.syringe_volumes[
            "right"], "Syringes are not the same size, this can create unexpected behaviour"
        while True:
            if not self.left_pump.get("is_pumping") and not self.right_pump.get("is_pumping"):
                self.left_valve.put("set_position", {"connect": "[[null,0],[2,3]]"})
                self.right_valve.put("set_position", {"connect": "[[null,0],[2,3]]"})
                #self.wait_until_idle(syringe=None)
                # ToDo Check if it's necessary to get valve's status (is_idle)
                # actuate syringes
                self.left_pump.put("set_to_volume", {"target_volume": to_volume_left, "rate": speed_left})
                self.right_pump.put("set_to_volume", {"target_volume": to_volume_right, "rate": speed_right})
                break
            else:
                sleep(0.01)

    def deliver_from_dual_syringes(self, to_volume_left: float = None, speed_left: float = None,
                                   to_volume_right: float = None, speed_right: float = None):
        """
        Assumes Input on left of valve and output on the right

        Args:
            to_volume:
            speed:

        Returns:

        """
        assert self.syringe_volumes["left"] == self.syringe_volumes[
            "right"], "Syringes are not the same size, this can create unexpected behaviour"
        # switch valves
        while True:
            if not self.left_pump.get("is_pumping") and not self.right_pump.get("is_pumping"):
                self.left_valve.put("set_position", {"connect": "[[null,null],[2,0]]"})
                self.right_valve.put("set_position", {"connect": "[[null,null],[2,0]]"})
                # self.wait_until_idle(syringe=None)
                # ToDo Check if it's necessary to get valve's status (is_idle)
                # actuate syringes
                self.left_pump.put("set_to_volume", {"target_volume": to_volume_left, "rate": speed_left})
                self.right_pump.put("set_to_volume", {"target_volume": to_volume_right, "rate": speed_right})
                break
            else:
                sleep(0.01)
