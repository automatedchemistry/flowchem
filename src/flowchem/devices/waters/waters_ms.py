"""
This is an ugly attempt to control a Waters Xevo MS via Autolynx.
When the MS is running and Autolynx is running, measuring an MS only requires putting a csv file with specific header
into a specific (and installation dependent) folder.
The Aim of this code is to supply a class that deals with creating the file with right experiment code and fields and
dropping it to the right folder.
https://www.waters.com/webassets/cms/support/docs/71500123505ra.pdf
"""
from pathlib import Path
import subprocess
import asyncio
from pathlib import Path
from shutil import which

from loguru import logger

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import jakob, miguel

from .waters_ms_component import WatersMSControl

# autolynx queue file is also where the conversion should happen - just set duration and a bit after that issue the conversion command
class WatersMS(FlowchemDevice):
    """
    Control class for Waters Xevo MS via Autolynx.

    While MS and Autolynx are running, running samples only requires putting a csv file with specific header into a specific (and installation dependent) folder.
    """
    def __init__(self,
                 name: str = "Waters_MS",
                 path_to_AutoLynxQ: str = r"W:\BS-FlowChemistry\Equipment\Waters MS\AutoLynxQ",
                 ms_exp_file: str = "15min_scan.exp",
                 tune_file: str = "SampleTuneAndDev_ManOBz_MeOH_after_geom.ipr",
                 inlet_method: str = "inlet_method",
                 ) -> None:
        super().__init__(name=name)
        # Metadata
        self.device_info.authors = [jakob, miguel]
        self.device_info.manufacturer = "Waters"
        self.device_info.model = "Waters Mass Spectrometer"

        self.fields = "FILE_NAME\tMS_FILE\tMS_TUNE_FILE\tINLET_FILE\tSAMPLE_LOCATION\tIndex"
        self.rows = f"\t{ms_exp_file}\t{tune_file}\t{inlet_method}\t66\t1"
        self.queue_path = Path(path_to_AutoLynxQ)
        self.run_duration = None

    async def initialize(self):
        """Assign components."""
        self.components.append(WatersMSControl(name="mass_spectrometer", hw_device=self))

    def record_mass_spec(self, sample_name: str, run_duration: int = 0, queue_name = "next.txt", do_conversion: bool = False):
        # Autolynx behaves weirdly, it expects a .txt file and that the fields are separated by tabs. A csv file
        # separated w commas however does not work... Autolynx has to be set to look for csv files
        file_path = self.queue_path/Path(queue_name)
        with open(file_path,'w') as f:
            f.write(self.fields)
            f.write(f"\n{sample_name}{self.rows}")
        if do_conversion:
            c = Converter(output_dir=r"W:\BS-FlowChemistry\data\open_format_ms")
            # get filename
            # get run duration
            c.convert_masspec(str(sample_name), run_delay=run_duration+60)


# convert to mzml C:\Users\BS-flowlab\AppData\Local\Apps\ProteoWizard 3.0.22198.0867718 64-bit>
class Converter:

    def __init__(self, path_to_executable = r"C:\Users\BS-flowlab\AppData\Local\Apps\ProteoWizard 3.0.22198.0867718 64-bit",
                 output_dir = r"W:\BS-FlowChemistry\data\open_format_ms",
                 raw_data=r"W:\BS-FlowChemistry\data\MS_Jakob.PRO\Data"):
        self.raw_data = raw_data
        self.exe = path_to_executable
        self.output_dir = output_dir

# open subprocess in this location
    def convert_masspec(self, filename, run_delay: int = 0):

        assert 0 <= run_delay <= 9999
        if ".raw" not in filename:
            filename = filename + ".raw"
        filename_w_path_ending = Path(self.raw_data)/Path(filename)
        # create string
        exe_str = f"msconvert {filename_w_path_ending} -o {self.output_dir}"
        if run_delay:
            # execute conversion w delay
            exe_str = f"ping -n {run_delay} 127.0.0.1 >NUL && {exe_str}"

        subprocess.Popen(exe_str, cwd=self.exe, shell=True)
        #x.run(exe_str, shell=True, capture_output=False, timeout=3)


if __name__ == "__main__":
    # seems to work - now, a comparison is needed of what is present already and what new
    proprietary_data_path = Path(r"W:\BS-FlowChemistry\data\MS_Jakob.PRO\Data")
    open_data_path = Path(r"W:\BS-FlowChemistry\data\open_format_ms")
    conv = Converter(output_dir=str(open_data_path))
    converted = []
    prop=[]
    for i in proprietary_data_path.rglob("*.raw"):
        prop.append(i.stem)
    for j in open_data_path.rglob("*.mzML"):
        converted.append(j.stem)
    unique = set(converted).symmetric_difference(set(prop))
    print(unique)
    for i in unique:
        x=proprietary_data_path.rglob(i.strip() + ".raw")
        print(x)
        try:
            conv.convert_masspec(str(next(x)))
        except StopIteration:
            pass