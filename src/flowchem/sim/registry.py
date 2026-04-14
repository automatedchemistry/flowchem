"""
Simulation registry — maps every real device class name to its sim counterpart.

Keys   : the string that appears as ``type`` in a TOML config file.
Values : fully-qualified class path of the replacement sim class.

When ``flowchem-sim`` starts it replaces the autodiscovered device mapper
with the classes listed here.  Any device type found in the TOML that has
*no* entry here raises a clear ``NotImplementedError`` at startup rather
than attempting a real hardware connection.

Adding a new device
-------------------
1. Create ``src/flowchem/sim/devices/<vendor>/<device>_sim.py``
2. Implement ``<DeviceSim>`` subclassing the real device class (or
   FlowchemDevice directly when the real __init__ calls the SDK).
3. Override ``from_config`` to skip serial/network/SDK init.
4. Add an entry to ``_REGISTRY`` below.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# Registry — every supported device family
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, str] = {
    # Hamilton
    "ML600": "flowchem.sim.devices.hamilton.ml600_sim.ML600Sim",
    # Knauer
    "AzuraCompact": "flowchem.sim.devices.knauer.azura_compact_sim.AzuraCompactSim",
    "KnauerValve": "flowchem.sim.devices.knauer.knauer_valve_sim.KnauerValveSim",
    "KnauerAutosampler": "flowchem.sim.devices.knauer.autosampler_sim.KnauerAutosamplerSim",
    "KnauerDAD": "flowchem.sim.devices.knauer.dad_sim.KnauerDADSim",
    # Huber
    "HuberChiller": "flowchem.sim.devices.huber.huber_sim.HuberChillerSim",
    # Harvard Apparatus
    "Elite11": "flowchem.sim.devices.harvardapparatus.elite11_sim.Elite11Sim",
    # Vacuubrand
    "CVC3000": "flowchem.sim.devices.vacuubrand.cvc3000_sim.CVC3000Sim",
    # Manson
    "MansonPowerSupply": "flowchem.sim.devices.manson.manson_sim.MansonPowerSupplySim",
    # Bronkhorst
    "MFC": "flowchem.sim.devices.bronkhorst.bronkhorst_sim.MFCSim",
    "EPC": "flowchem.sim.devices.bronkhorst.bronkhorst_sim.EPCSim",
    # Vapourtec
    "R2": "flowchem.sim.devices.vapourtec.r2_sim.R2Sim",
    "R4Heater": "flowchem.sim.devices.vapourtec.r4_sim.R4HeaterSim",
    # Runze
    "RunzeValve": "flowchem.sim.devices.runze.runze_sim.RunzeValveSim",
    # Vici Valco
    "ViciValve": "flowchem.sim.devices.vicivalco.vici_sim.ViciValveSim",
    # Phidgets
    "PhidgetPressureSensor": "flowchem.sim.devices.phidgets.phidgets_sim.PhidgetPressureSensorSim",
    "PhidgetBubbleSensor": "flowchem.sim.devices.phidgets.bubble_sim.PhidgetBubbleSensorSim",
    "PhidgetPowerSource5V": "flowchem.sim.devices.phidgets.bubble_sim.PhidgetPowerSource5VSim",
    # Mettler-Toledo
    "IcIR": "flowchem.sim.devices.mettlertoledo.icir_sim.IcIRSim",
    # Magritek
    "Spinsolve": "flowchem.sim.devices.magritek.spinsolve_sim.SpinsolveSim",
    # Waters
    "WatersMS": "flowchem.sim.devices.waters.waters_sim.WatersMSSim",
    # DataApex
    "Clarity": "flowchem.sim.devices.dataapex.clarity_sim.ClaritySim",
    # Custom MPIKG devices
    "SwitchBoxMPIKG": "flowchem.sim.devices.custom.switchbox_sim.SwitchBoxMPIKGSim",
    "PeltierCooler": "flowchem.sim.devices.custom.peltier_sim.PeltierCoolerSim",
    # Bio-Chem solenoid valves
    "BioChemSolenoidValve": "flowchem.sim.devices.biochem.solenoid_sim.BioChemSolenoidValveSim",
    "BioChemSolenoid2WayValve": "flowchem.sim.devices.biochem.solenoid_sim.BioChemSolenoid2WayValveSim",
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def _load_class(dotted_path: str) -> Any:
    """Import and return a class given its fully-qualified dotted path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, class_name)


def build_sim_device_mapper(real_mapper: dict[str, Any]) -> dict[str, Any]:
    """
    Replace every real device class in *real_mapper* with its sim counterpart.

    Parameters
    ----------
    real_mapper:
        The dict returned by ``autodiscover_device_classes()``, mapping
        device-type strings to real device classes.

    Returns
    -------
    dict
        A new mapper where every key present in ``_REGISTRY`` is replaced by
        the corresponding sim class.  Keys absent from ``_REGISTRY`` are
        replaced by a placeholder class that raises ``NotImplementedError``
        on instantiation with a helpful message.
    """
    sim_mapper: dict[str, Any] = {}

    for device_type, real_cls in real_mapper.items():
        if device_type in _REGISTRY:
            sim_cls = _load_class(_REGISTRY[device_type])
            logger.info(
                f"[SIM] '{device_type}' ({real_cls.__name__}) " f"→ {sim_cls.__name__}"
            )
            sim_mapper[device_type] = sim_cls
        else:
            sim_mapper[device_type] = _make_unsupported_placeholder(
                device_type, real_cls
            )

    return sim_mapper


def _make_unsupported_placeholder(device_type: str, real_cls: Any) -> Any:
    """
    Return a thin wrapper around *real_cls* whose ``from_config`` / ``__init__``
    immediately raises ``NotImplementedError`` with a helpful message.
    """

    class _UnsupportedSim(real_cls):  # type: ignore[valid-type]
        @classmethod
        def from_config(cls, **kwargs):
            raise NotImplementedError(
                f"No simulation implementation exists for device type "
                f"'{device_type}'.\n"
                f"Add an entry to flowchem/sim/registry.py to enable "
                f"simulation support."
            )

        def __init__(self, *args, **kwargs):
            raise NotImplementedError(
                f"No simulation implementation exists for device type "
                f"'{device_type}'.\n"
                f"Add an entry to flowchem/sim/registry.py to enable "
                f"simulation support."
            )

    _UnsupportedSim.__name__ = f"{device_type}SimNotImplemented"
    return _UnsupportedSim
