"""
Control a Waters Xevo MS via Autolynx.
When the MS is running and Autolynx is running, measuring an MS only requires putting a csv file with specific header
into a specific (and installation dependent) folder.
The Aim of this code is to supply a class that deals with creating the file with right experiment code and fields and
dropping it to the right folder.
https://www.waters.com/webassets/cms/support/docs/71500123505ra.pdf
"""

import subprocess
from pathlib import Path

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import jakob, miguel

from .waters_ms_component import WatersMSControl


class WatersMS(FlowchemDevice):
    """
    Interface to control Waters Xevo MS through AutoLynx queue files.

    This class creates and writes a properly formatted tab-delimited queue file that
    AutoLynx reads to start MS data acquisition. It can also optionally invoke
    post-run data conversion via ProteoWizard's `msconvert`.

    Args:
        name (str): Name of the device.
        path_to_AutoLynxQ (str): Path to the AutoLynx queue folder.
        ms_exp_file (str): Name of the MS experiment method file.
        tune_file (str): Name of the tune method file.
        inlet_method (str): Name of the inlet method file.
    """

    def __init__(
        self,
        name: str = "Waters_MS",
        path_to_AutoLynxQ: str = r"PATH/TO/AutoLynxQ",
        ms_exp_file: str = "",
        tune_file: str = "",
        inlet_method: str = "inlet_method",
    ) -> None:
        super().__init__(name=name)

        self.device_info.authors = [jakob, miguel]
        self.device_info.manufacturer = "Waters"
        self.device_info.model = "Waters Mass Spectrometer"

        self.fields = (
            "FILE_NAME\tMS_FILE\tMS_TUNE_FILE\tINLET_FILE\tSAMPLE_LOCATION\tIndex"
        )

        self.queue_path = Path(path_to_AutoLynxQ)
        self.run_duration = None

        self.ms_exp_file = ms_exp_file
        self.tune_file = tune_file
        self.inlet_method = inlet_method
        self.sample_location = "66"
        self.index = "1"

    async def initialize(self):
        """Assign components."""
        self.components.append(
            WatersMSControl(name="mass_spectrometer", hw_device=self)
        )

    def _build_queue_row(self, sample_name: str) -> str:
        return (
            f"{sample_name}\t"
            f"{self.ms_exp_file}\t"
            f"{self.tune_file}\t"
            f"{self.inlet_method}\t"
            f"{self.sample_location}\t"
            f"{self.index}"
        )

    async def set_method(
            self,
            ms_exp_file: str,
            tune_file: str | None = None,
            inlet_method: str | None = None,
    ) -> bool:
        """
        Set the MS acquisition method parameters that will be used for the next run(s).
        """
        self.ms_exp_file = ms_exp_file

        if tune_file is not None:
            self.tune_file = tune_file

        if inlet_method is not None:
            self.inlet_method = inlet_method

        return True

    async def record_mass_spec(
            self,
            sample_name: str,
            run_duration: int = 0,
            queue_name: str = "next.txt",
            do_conversion: bool = False,
            output_dir: str = r"PATH/TO/open_format_ms",
    ) -> bool:
        """
        Create and drop a queue file for AutoLynx to initiate MS acquisition.

        Args:
            sample_name (str): Base name for the output MS data file.
            run_duration (int): Estimated duration of the MS acquisition (in seconds).
            queue_name (str): Name of the AutoLynx queue file to write.
            do_conversion (bool): If True, automatically convert raw data to mzML format after delay.
            output_dir (str): Directory to store converted `.mzML` files.
        """
        # Autolynx behaves weirdly, it expects a .txt file and that the fields are separated by tabs. A csv file
        # separated w commas however does not work... Autolynx has to be set to look for csv files
        if not self.ms_exp_file:
            raise ValueError("No MS method set. Please call set_method first.")

        file_path = self.queue_path / Path(queue_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.fields)
            f.write(f"\n{self._build_queue_row(sample_name)}")

        if do_conversion:
            c = Converter(output_dir=output_dir)
            c.convert_masspec(str(sample_name), run_delay=run_duration + 60)

        return True


# convert to mzml 64-bit
class Converter:
    """
    Handles conversion of proprietary Waters `.raw` MS data to `.mzML` format.

    This is done via the `msconvert` utility from ProteoWizard, optionally delayed to
    allow MS acquisition to complete.

    Args:
        path_to_executable (str): Path to the folder containing `msconvert.exe`.
        output_dir (str): Output directory for converted `.mzML` files.
        raw_data (str): Directory containing `.raw` data from the MS.
    """

    def __init__(
        self,
        path_to_executable=r"PATH/TO/ProteoWizard 64-bit",
        output_dir=r"PATH/TO/open_format_ms",
        raw_data=r"PATH/TO/Data",
    ):
        self.raw_data = raw_data
        self.exe = path_to_executable
        self.output_dir = output_dir

    # open subprocess in this location
    def convert_masspec(self, filename, run_delay: int = 0):
        """
        Convert a `.raw` MS data file to `.mzML` using msconvert.

        Args:
            filename (str): Filename of the `.raw` file to convert (with or without `.raw` extension).
            run_delay (int): Optional delay (in seconds) before running the conversion command.
                             Useful for waiting until acquisition is complete.

        Raises:
            AssertionError: If `run_delay` is not within the range 0–9999 seconds.
        """
        assert 0 <= run_delay <= 9999
        if ".raw" not in filename:
            filename = filename + ".raw"
        filename_w_path_ending = Path(self.raw_data) / Path(filename)
        # create string
        exe_str = f"msconvert {filename_w_path_ending} -o {self.output_dir}"
        if run_delay:
            # execute conversion w delay
            exe_str = f"ping -n {run_delay} 127.0.0.1 >NUL && {exe_str}"

        subprocess.Popen(exe_str, cwd=self.exe, shell=True)


if __name__ == "__main__":
    proprietary_data_path = Path(r"PATH/TO/Data")
    open_data_path = Path(r"PATH/TO/open_format_ms")
    conv = Converter(output_dir=str(open_data_path))
    converted = []
    prop = []
    for i in proprietary_data_path.rglob("*.raw"):
        prop.append(i.stem)
    for j in open_data_path.rglob("*.mzML"):
        converted.append(j.stem)
    unique = set(converted).symmetric_difference(set(prop))
    print(unique)
    for i in unique:  # type: ignore
        x = proprietary_data_path.rglob(i.strip() + ".raw")  # type: ignore
        print(x)
        try:
            conv.convert_masspec(str(next(x)))
        except StopIteration:
            pass
