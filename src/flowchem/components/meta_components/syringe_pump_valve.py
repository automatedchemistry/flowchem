from time import sleep
from loguru import logger
from flowchem import ureg
from flowchem.client.component_client import FlowchemComponentClient


def create_syringe_pump(flowchem_devices, config, volume="1 ml"):
    name, pump_part, valve_part = config.split(".")
    return SyringePumpValve(
        pump=flowchem_devices[name][pump_part],
        valve=flowchem_devices[name][valve_part],
        syringe_volume=ureg.Quantity(volume),
    )

class SyringePumpValve:
    """
    Syringe pump + valve meta component.
    """
    def __init__(self, pump=None, valve=None, syringe_volume: ureg.Quantity | None = None):
        self.pump: FlowchemComponentClient = pump
        self.valve: FlowchemComponentClient = valve
        self.syringe_volume = syringe_volume
        if not syringe_volume.check("[volume]"):
            raise ValueError("syringe_volume must be a quantity with units of volume (e.g., 'ml').")

    def fill_syringe(self, volume: ureg.Quantity, flowrate: ureg.Quantity, connect: str ="[[null,1],[null,0]]"):
        """

        """
        if not flowrate.check("[volume] / [time]"):
            raise ValueError("Flowrate must be a quantity with units of volume per time (e.g., 'ml/min').")
        if not volume.check("[volume]"):
            raise ValueError("Volume must be a quantity with units of volume (e.g., 'ml').")
        # switch valves
        self.wait_until_idle()
        self.valve.put("set_position", {"connect": connect})
        self.wait_until_idle()
        curr_vol = self.pump.get("get_current_volume")
        to_vol = curr_vol + volume
        to_vol = round(to_vol.m_as("ml"), 3)
        self.pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(flowrate)})

    def deliver_from_syringe(self, volume_to_deliver: ureg.Quantity, flowrate: ureg.Quantity , connect: str ="[[null,1],[null,0]]", syringe="left"):
        """

        """
        # Check if desired units
        if not flowrate.check("[volume] / [time]"):
            raise ValueError("Flowrate must be a quantity with units of volume per time (e.g., 'ml/min').")
        if not volume_to_deliver.check("[volume]"):
            raise ValueError("Volume must be a quantity with units of volume (e.g., 'ml').")
        self.wait_until_idle()
        self.valve.put("set_position", {"connect": connect})
        self.wait_until_idle()
        curr_vol = self.pump.get("get_current_volume")
        to_vol = curr_vol + volume_to_deliver
        to_vol = round(to_vol.m_as("ml"), 3)
        self.pump.put("set_to_volume", {"target_volume": f"{to_vol} ml", "rate": str(flowrate)})

    def wait_until_idle(self):
        """ Waits for pump to be idle. """
        logger.debug(f"wait until both pumps idle")
        while self.pump.get("is_pumping"):
            sleep(0.001)

    def home_syringe(self,
                     flowrate: ureg.Quantity | None = None,
                     connect=""):
        """
        Homes syringe.
        """
        # Defaults to twice the volume in ml/min
        if not flowrate:
            flowrate = ureg.Quantity(f"{self.syringe_volume["left"].m_as("ml") * 2} ml/min")
        # Checks for unit
        if not flowrate.check("[volume] / [time]"):
            raise ValueError("Flowrate must be a quantity with units of volume per time (e.g., 'ml/min').")
        self.pump.get("wait_until_idle")
        self.valve.put("set_position", {"connect": connect})
        self.pump.get("wait_until_idle")
        self.pump.put("set_to_volume", {"volume": "0 ml", "rate": str(flowrate)})



