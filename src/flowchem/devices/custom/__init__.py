"""custom devices."""
from .peltier_cooler import PeltierCooler
from .mpikg_switch_box import SwitchBoxMPIKG
from .virtual_peltier_cooler import VirtualPeltierCooler

__all__ = ["PeltierCooler", "VirtualPeltierCooler", "SwitchBoxMPIKG"]
