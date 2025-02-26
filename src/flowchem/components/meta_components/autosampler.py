"""
Module for communication with Autosampler.
"""
# For future: go through graph, acquire mac addresses, check which IPs these have and setup communication.
# To initialise the appropriate device on the IP, use class name like on chemputer
from loguru import logger

from enum import Enum, auto
from typing import Type, List
from time import sleep

import pandas as pd
from pandas import DataFrame
from flowchem import ureg
from rdkit.Chem import MolFromSmiles, MolToSmiles
from pathlib import Path

from flowchem.client.component_client import FlowchemComponentClient


# TODO assert that writing to and reloading works reliably - so use old mapping if it exists, here ro from platform code
try:
    # noinspection PyUnresolvedReferences
    from NDA_knauer_AS.knauer_AS import *

    HAS_AS_COMMANDS = True
except ImportError:
    HAS_AS_COMMANDS = False


def canonize_smiles(smiles:str):
    return MolToSmiles(MolFromSmiles(smiles))


def set_vial_content(substance, return_special_vial=False):
    try:
        return canonize_smiles(substance)
    except Exception as e:
        if not str(e).startswith("Python argument types in"):
            raise e
        else:
            pass
    try:
        return _SpecialVial(substance.lower()).value
    except ValueError as e:
        e.args += ("Either  you did not provide a valid string, not a valid special position, or both",)
        raise e


def check_special_vial(substance) -> bool:
    try:
        _SpecialVial(substance)
        return True
    except ValueError as e:
        return False


class _SpecialVial(Enum):
    CARRIER = "carrier"
    INERT_GAS = "gas"


class Vial:
        
    def __init__(self, substance, solvent: str or None, concentration: str, contained_volume: str, remaining_volume: str):

        self._remaining_volume = ureg.Quantity(remaining_volume)
        self._contained_volume = ureg.Quantity(contained_volume)
        self.substance = set_vial_content(substance)  # todo get this canonical
        if not check_special_vial(substance):
            self.solvent = solvent
            self.concentration = ureg.Quantity(concentration)
        else:
            self.solvent = None
            self.concentration = None

    def extract_from_vial(self, volume: str):
        if type(volume) is str:
            volume = ureg.Quantity(volume)
        self._contained_volume -= volume
    
    @property
    def available_volume(self) -> ureg.Quantity.Quantity:
        return self._contained_volume-self._remaining_volume


class TrayPosition:
    """basically, only acts a s container internally and to make substance access easy"""
    def __init__(self, side, row, column):
        self.side = side
        self.row = row
        self.column = column
        self.valid_position()

    def valid_position(self):
        from numpy import int64
        assert (self.side.upper() == SelectPlatePosition.LEFT_PLATE.name or self.side.upper() ==
                SelectPlatePosition.RIGHT_PLATE.name)
        assert type(self.row) in [int64, int]
        assert self.column is str and len(self.column) == 1


class Tray:
    def __init__(self, tray_type, persistant_storage: str):
        # todo set a path for continuous storing of layout
        self.tray_type = tray_type
        self.persistant = persistant_storage
        self._loaded_fresh: bool | None = None
        self.available_vials: DataFrame = self.load_submitted()
        self.check_validity_and_normalise()
        self._layout = ["Content", "Side", "Column", "Row", "Solvent", "Concentration", "ContainedVolume",
                        "RemainingVolume"]

    def load_submitted(self):
        # create the layout in Excel -> makes usage easy
        try:
            path = self._old_loading()
            return pd.read_excel(path) if not "json" in path.name else pd.read_json(path)
        except FileNotFoundError as e:
            e.args += (f"Fill out excel file under {self.persistant}.",)
            self.create_blank(self.persistant)
            raise e

# todo if loading submitted, check if a out file exists with same name. if not, check if a json checkpoint file exists.
    # if so, load thejson file and create the out file. Now, ask the user which should be used. if the out file is
    # loaded, delete the old out file, directly write the json file (before deleting)
    # with that procedure, it should always be the updated file used

    def _old_loading(self) -> Path:
        output = self.create_output_path(extended_file_name="_out")
        checkpoint = self.create_output_path(file_ending="json")

        if Path(output).exists():
            # if an output excel was written load that
            to_load = output
            user = input(f"You are about to load the AutoSampler Tray layout from {to_load}. This means You are using a "
                       f"previously properly finished experiments layout. Type 'YES' and hit enter to proceed,"
                       f" anything else will quit")
            self._loaded_fresh = False

        elif Path(checkpoint).exists():
            to_load = checkpoint
            user = input(f"You are about to load the AutoSampler Tray layout from {to_load}. This means You are using a "
                       f"previously intermittantly closed experiments layout. Type 'YES' and hit enter to proceed, anything else will quit")
            self._loaded_fresh = False
        else:
            to_load = Path(self.persistant)
            user = input(f"You are about to load the AutoSampler Tray layout from {to_load}. This means You are using a "
                       f"absolutely fresh layout. Type 'YES' and hit enter to proceed, anything else will quit")
            self._loaded_fresh = True
        if user == "YES":
            return to_load
        else:
            raise ValueError

    def check_validity_and_normalise(self):
        # normalize the dataframe
        self.available_vials["Content"] = self.available_vials["Content"].apply(set_vial_content)
        # make sure all unit ones are a unit
        self.available_vials[["Concentration", "ContainedVolume", "RemainingVolume"]].map(ureg, na_action="ignore")
        assert self.available_vials["Column"].apply(lambda x: x.lower() in list("abcdef")).all(), "Your column has wrong values"
        assert self.available_vials["Side"].apply(lambda x: x.upper() in [SelectPlatePosition.RIGHT_PLATE.name, SelectPlatePosition.LEFT_PLATE.name]).all(), "Your sample side has wrong values"
        assert self.available_vials["Row"].apply(lambda x: x <= 8).all(), "Your row has wrong values"
        self.save_current()
        
    def get_unique_chemicals(self) -> List[str]:
        """
        Get the unique SMILES strings from the available samples
        Returns:
            list:   List of unique SMILES strings
        """
        # drop duplicates
        single_values = self.available_vials["Content"].drop_duplicates()
        return [x for x in single_values if not check_special_vial(x)]

    def load_entry(self, index:int) -> [Vial, TrayPosition]:
        # return vial for updating volume, return TrayPosiition to go there, via Tray update the json
        # get position and substance from dataframe, do based on index
        entry=self.available_vials.loc[index]
        return Vial(entry["Content"], entry["Solvent"], entry["Concentration"], entry["ContainedVolume"], entry["RemainingVolume"]), TrayPosition(entry["Side"], entry["Row"], entry["Column"])

    def find_vial(self, contains:str, min_volume: str="0 mL")-> int or None:
        min_volume = ureg.Quantity(min_volume) if type(min_volume) is str else min_volume
        right_substance = self.available_vials["Content"] == contains
        lowest_vol = self.available_vials.loc[right_substance]
        new = lowest_vol["ContainedVolume"].map(lambda x: ureg.Quantity(x).m_as("mL")) - lowest_vol["RemainingVolume"].map(lambda x: ureg.Quantity(x).m_as("mL")) - (min_volume.m_as("mL"))
        new = new[new >= 0]
        try:
            return new.idxmin()
        except ValueError:
            return None

    def find_lowest_volume_vial(self, identifier: List[str], min_volume=0.07) -> int or None:
        """
        Find the vial with the lowest volume of a list of substances
        Args:
            identifier: list of smiles to check for
            min_volume: minimum volume to be considered in mL

        Returns:
            index of the vial with the lowest volume. If all are the same, it simply returns some
        """
        # find the lowest volume over a list of substances
        right_substances = self.available_vials.loc[self.available_vials["Content"].isin(identifier)]
        new = right_substances["ContainedVolume"].map(ureg).map(lambda x: x.m_as("mL")) - right_substances["RemainingVolume"].map(ureg).map(lambda x: x.m_as("mL"))
        new = new.where(lambda x: x >= min_volume)
        if new.isnull().all():
            return None
        else:
            return new.idxmin(skipna=True)

    # this is mostly for updating volume
    def update_volume(self, index, vial: Vial, save=True):
        # modify entry, based on index
        self.available_vials.at[index, "ContainedVolume"] = f"{round(vial._contained_volume.m_as('mL'), 3)} mL"
        if save:
            self.save_current()

    # constantly update the json file
    def save_current(self):
        write_to = self.create_output_path(file_ending="json")
        # todo just overwrite? that's the current file
        with open(write_to, "w") as f:
            self.available_vials.to_json(f)
            
    def save_output(self):
        write_to = self.create_output_path(extended_file_name="_out")
        self.available_vials.to_excel(write_to)
        
    def create_output_path(self, extended_file_name=None, file_ending=None):
        output_name, output_ending = Path(self.persistant).name.split(".")
        write_to = Path(self.persistant).parent / Path(f"{output_name}{extended_file_name if extended_file_name else ''}.{file_ending if file_ending else output_ending}")
        return write_to

    def create_blank(self, path):
        if Path(path).exists():
            raise FileExistsError
        pd.DataFrame(columns=self._layout).to_excel(path)


class Autosampler:
    """
    Autosampler meta components.
    """
    def __init__(self, gantry3d=None, pump=None, syringe_valve=None, injection_valve=None, tray_mapping: Tray=None):
        # get statuses, that is basically syringe syize, volumes, plate type
        self.gantry3D: FlowchemComponentClient = gantry3d
        self.pump: FlowchemComponentClient = pump
        self.syringe_valve: FlowchemComponentClient = syringe_valve
        self.injection_valve: FlowchemComponentClient = injection_valve

        self.initialize()
        self.tray_mapping: Tray = tray_mapping

    def initialize(self):
        """
        Sets initial positions of components to assure reproducible startup
        Returns: None
        """
        self.gantry3D.put("reset_errors")
        self.gantry3D.put("set_z_position", {"position": "UP"})
        self.gantry3D.put("set_needle_position", {"position": "WASTE"})
        self.syringe_valve.put("set_monitor_position", {"position": "WASTE"})
        self.injection_valve.put("set_monitor_position", {"position": "LOAD"})

    def connect_chemical(self, chemical: str, volume_sample: str = "0 mL", volume_buffer: str = "0 mL", flow_rate=None):
        # needs to take plate layout and basically the key, so smiles or special denomination
        if not self.tray_mapping:
            logger.error("You must provide a tray mapping to access substances by name")
            raise ValueError("You must provide a tray mapping to access substances by name")
        else:
            vial_index = self.tray_mapping.find_vial(chemical, min_volume=volume_sample)
            if vial_index is None:
                logger.error(f"No vial contains enough sample for the desired volume")
                raise ValueError(f"No vial contains enough sample for the desired volume")
            vial, position = self.tray_mapping.load_entry(vial_index)
            self.gantry3D.put("connect_to_position", {"tray":  position.side, "row": position.row,
                                                      "column": position.column})
            # this waits for syringe to be ready as well per default
            self.wait_until_ready(wait_for_syringe=True)
            self.pick_up_sample(volume=ureg.Quantity(volume_sample).m_as("mL"), volume_buffer=ureg.Quantity(volume_buffer).m_as("ml"),
                                flow_rate=flow_rate if not flow_rate else ureg.Quantity(flow_rate).m_as("mL/min"))
            if vial.substance != _SpecialVial.INERT_GAS.value:
                vial.extract_from_vial(volume_sample)
            self.tray_mapping.update_volume(vial_index, vial)

    def wait_until_ready(self, wait_for_syringe: bool = True):
        """
        Wait for AS to be done
        Args:
            wait_for_syringe: If True (default), also the  syringe will be waited for.
                            If False it can run in background

        Returns: None

        """
        # todo wait for external syringe ready as well
        while True:
            if not self.gantry3D.get("is_needle_running"):  # Needle is not running
                if not self.pump.get("is_pumping"):  # Syringe is also not pumping
                    break
                elif not wait_for_syringe:  # If wait_for_syringe is False, break even if syringe is pumping
                    break
                else:
                    sleep(0.01)
            else:  # Needle is running
                sleep(0.01)

# it would be reasonable to get all from needle to loop, with piercing inert gas vial
    def disconnect_sample(self, move_plate = False):
        self.injection_valve.put("set_monitor_position",{"position": "LOAD"})
        self.gantry3D.put("set_z_position",{"position": "UP"})
        if move_plate:
            self.gantry3D.put("move_tray", {"tray": "NO_PLATE", "row": "HOME"})
            self.gantry3D.put("set_needle_position",{"position": "WASTE"})
            
    def fill_wash_reservoir(self, volume:float=0.2, flow_rate:float = None):
        self.syringe_valve.put("set_monitor_position",{"position": "WASH"})
        self.pump.put("withdraw",{"rate": flow_rate, "volume": volume})
        self.gantry3D.put("connect_to_position", {"tray": "WASH"})
        # aspirate does not await syringe execution, therefor explicit await is necessary
        self.wait_until_ready()
        # this is just used to connect the syringe to sample
        self.pick_up_sample(volume=0,flow_rate=flow_rate)
        # empty syringe into reservoir
        self.pump.put("infuse",{"rate": flow_rate, "volume": volume})
        self.wait_until_ready()
        self.disconnect_sample()
        
    def empty_wash_reservoir(self, volume: float = 0.2, flow_rate: float = None):
        # empty reservoir with syringe
        self.gantry3D.put("connect_to_position", {"tray": "WASH"})
        self.pick_up_sample(volume=volume, flow_rate=flow_rate)
        # go up and move to waste
        self.disconnect_sample()

    def wash_needle(self, volume: float = 0.2, times: int = 3, flow_rate: float = None):
        """
        Fill needle with solvent and then wash it.
        Args:
            volume: 0.2 mL is a reasonable value
            times:
            flow_rate:

        Returns: None

        """

        for i in range(times):
            # do wash reservoir fill
            # fill syringe here and go to right position
            self.fill_wash_reservoir(volume=volume, flow_rate=flow_rate)
            self.empty_wash_reservoir(volume=volume, flow_rate=flow_rate)
            self.gantry3D.put("set_needle_position",{"position": "WASTE"})
            self.gantry3D.put("set_z_position", {"position": "DOWN"})
            # dispense to waste and go up
            self.pump.put("infuse",{"rate": flow_rate, "volume": volume})
            self.wait_until_ready()
            self.gantry3D.put("set_z_position", {"position": "UP"})
        
        # fill here, and eject, without needle wash!
        self.syringe_valve.put("set_monitor_position",{"position": "WASH"})
        self.pump.put("withdraw",{"rate": flow_rate, "volume": volume})
        self.injection_valve.put("set_monitor_position",{"position": "INJECT"})
        self.gantry3D.put("set_needle_position",{"position": "WASTE"})
        self.gantry3D.put("set_z_position",{"position": "DOWN"})
        self.wait_until_ready()
        # eject directly to waste
        self.syringe_valve.put("set_monitor_position",{"position": "NEEDLE"})
        self.pump.put("infuse", {"rate": flow_rate*10 if flow_rate else flow_rate, "volume": volume})
        self.wait_until_ready()
        self.gantry3D.put("set_z_position",{"position": "UP"})

    def pick_up_sample(self, volume: float or int, volume_buffer=0, flow_rate=None):
        if volume_buffer:
            self.syringe_valve.put("set_monitor_position",{"position": "WASH"})
            self.pump.put("withdraw",{"rate": flow_rate, "volume": volume})
        self.injection_valve.put("set_monitor_position",{"position": "INJECT"})
        # wait until buffer taken
        self.wait_until_ready()
        self.syringe_valve.put("set_monitor_position",{"position": "NEEDLE"})
        self.pump.put("withdraw",{"rate": flow_rate, "volume": volume})
        # while picking up sample, there is no logical AS based background activity, so wait until ready
        self.wait_until_ready()

    def wash_system(self, times: int = 3, flow_rate=None, volume: float = 0.250, dispense_to: str = "needle"):
        """

        Args:
            times: How often to wash
            flow_rate: Which flowrate to wash with. Only works with external syringe, otherwise use default value
            volume: washing volume in mL
            dispense_to: Where to dispense the washing fluid to - so which path to clean. Options are needle, outside, waste

        Returns: None

        """
        # washing loop, ejecting through needle!
        legal_arguments = ["needle", "outside", "waste"]
        if dispense_to not in legal_arguments:
            raise NotImplementedError(f"Dispense to can only take following values {legal_arguments}.")
        self.gantry3D.put("set_needle_position",{"position": "WASTE"})
        for i in range(times):
            self.syringe_valve.put("set_monitor_position",{"position": "WASH"})
            self.pump.put("withdraw",{"rate": flow_rate, "volume": volume})
            self.wait_until_ready()
            if dispense_to == legal_arguments[0]:
                self.syringe_valve.put("set_monitor_position",{"position": "NEEDLE"})
                self.injection_valve.put("set_monitor_position",{"position": "INJECT"})
                self.gantry3D.put("set_z_position",{"position": "DOWN"})
            elif dispense_to == legal_arguments[1]:
                self.syringe_valve.put("set_monitor_position",{"position": "NEEDLE"})
                self.injection_valve.put("set_monitor_position",{"position": "LOAD"})
            elif dispense_to == legal_arguments[2]:
                self.syringe_valve.put("set_monitor_position",{"position": "WASTE"})
            self.pump.put("infuse",{"rate": flow_rate, "volume": volume})
            self.wait_until_ready()
            self.gantry3D.put("set_z_position",{"position": "UP"})

    def dispense_sample(self, volume: float, dead_volume=0.050, flow_rate=None):
        """
        Dispense Sample in buffer tube to device connected to AS. This does not await end of dispensal.
         You have to do that explicitly
        Args:
            volume: Volume to dispense in mL
            dead_volume: Dead volume to dispense additionally
            flow_rate: Flow rate, only works w external syringe
            
        Returns: None
        
        """
        self.syringe_valve.put("set_monitor_position",{"position": "NEEDLE"})
        self.injection_valve.put("set_monitor_position",{"position": "LOAD"})
        self.pump.put("infuse", {"rate": flow_rate, "volume": volume+dead_volume})

if __name__ == "__main__":
    pass