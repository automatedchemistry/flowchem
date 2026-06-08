"""Async implementation of FlowIR."""

import asyncio
import datetime
from pathlib import Path

from asyncua import Client, ua
from asyncua.ua.uaerrors import BadOutOfService, Bad
from loguru import logger
from pydantic import BaseModel

from flowchem.components.analytics.ir import IRSpectrum
from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.mettlertoledo.icir_control import IcIRControl
from flowchem.utils.exceptions import DeviceError
from flowchem.utils.people import dario, jakob, wei_hsin


class ProbeInfo(BaseModel):
    """Dictionary returned from iCIR with probe info."""

    spectrometer: str
    spectrometer_SN: int
    probe_SN: int
    detector: str
    apodization: str
    ip_address: str
    probe_type: str
    sampling_interval: str
    resolution: int
    scan_option: str
    gain: int


class IcIR(FlowchemDevice):
    """Object to interact with the iCIR software controlling the FlowIR and ReactIR."""

    iC_OPCUA_DEFAULT_SERVER_ADDRESS = "opc.tcp://localhost:62552/iCOpcUaServer"
    _supported_versions = {"7.1.91.0"}
    SOFTWARE_VERSION = "ns=2;s=Local.iCIR.SoftwareVersion"
    CONNECTION_STATUS = "ns=2;s=Local.iCIR.ConnectionStatus"
    PROBE_DESCRIPTION = "ns=2;s=Local.iCIR.Probe1.ProbeDescription"
    PROBE_STATUS = "ns=2;s=Local.iCIR.Probe1.ProbeStatus"
    LAST_SAMPLE_TIME = "ns=2;s=Local.iCIR.Probe1.LastSampleTime"
    SAMPLE_COUNT = "ns=2;s=Local.iCIR.Probe1.SampleCount"
    SPECTRA_TREATED = "ns=2;s=Local.iCIR.Probe1.SpectraTreated"
    SPECTRA_RAW = "ns=2;s=Local.iCIR.Probe1.SpectraRaw"
    SPECTRA_BACKGROUND = "ns=2;s=Local.iCIR.Probe1.SpectraBackground"
    START_EXPERIMENT = "ns=2;s=Local.iCIR.Probe1.Methods.Start Experiment"
    STOP_EXPERIMENT = "ns=2;s=Local.iCIR.Probe1.Methods.Stop"
    METHODS = "ns=2;s=Local.iCIR.Probe1.Methods"

    counter = 0

    def __init__(self, template="", url="", name="") -> None:
        """Initiate connection with OPC UA server."""
        super().__init__(name)
        self.device_info = DeviceInfo(
            authors=[dario, jakob, wei_hsin],
            manufacturer="Mettler-Toledo",
            model="iCIR",
            version="",
        )

        # Default (local) url if none provided
        if not url:
            url = self.iC_OPCUA_DEFAULT_SERVER_ADDRESS
        self.opcua = Client(
            url,
            timeout=5,
        )  # Call to START_EXPERIMENT can take few seconds!

        self._template = template

    async def initialize(self):
        """Initialize, check connection and start acquisition."""
        try:
            await self.opcua.connect()
        except asyncio.TimeoutError as timeout_error:
            raise DeviceError(
                f"Could not connect to iCIR on {self.opcua.server_url}!"
            ) from timeout_error

        # Ensure iCIR version is supported
        self.device_info.version = await self.opcua.get_node(
            self.SOFTWARE_VERSION,
        ).get_value()  # e.g. "7.1.91.0"

        self.ensure_version_is_supported()
        logger.debug("iCIR initialized!")

        if not await self.is_iCIR_connected():
            raise DeviceError("Device not connected! Check iCIR...")

        # Start acquisition! Ensures the device is ready when a spectrum is needed
        await self.start_experiment(name="Flowchem", template=self._template)
        probe = await self.probe_info()
        self.device_info.additional_info = probe.model_dump()

        # Set IRSpectrometer component
        self.components.append(IcIRControl("ir-control", self))

    def is_local(self):
        """Return true if the server is on the same machine running the python code."""
        return any(
            x in self.opcua.server_url.netloc for x in ("localhost", "127.0.0.1")
        )

    def ensure_version_is_supported(self):
        """Check if iCIR is installed and open and if the version is supported."""
        try:
            if self.device_info.version not in self._supported_versions:
                logger.warning(
                    f"The current version of iCIR [self.version] has not been tested!"
                    f"Pleas use one of the supported versions: {self._supported_versions}",
                )
        except ua.UaStatusCodeError as error:  # iCIR app closed
            raise DeviceError(
                "iCIR app not installed or closed or no instrument available!"
            ) from error

    # noinspection PyPep8Naming
    async def is_iCIR_connected(self) -> bool:
        """Check connection with instrument."""
        return await self.opcua.get_node(self.CONNECTION_STATUS).get_value()

    async def probe_info(self) -> ProbeInfo:
        """Return FlowIR probe information."""
        probe_info = await self.opcua.get_node(self.PROBE_DESCRIPTION).get_value()
        return self.parse_probe_info(probe_info)

    async def probe_status(self):
        """Return current probe status. Possible values are 'Running', 'Not running' (+ more?)."""
        return await self.opcua.get_node(self.PROBE_STATUS).get_value()

    async def last_sample_time(self) -> datetime.datetime:
        """Return date/time of the latest scan."""
        return await self.opcua.get_node(self.LAST_SAMPLE_TIME).get_value()

    async def sample_count(self) -> int | None:
        """Sample count (integer autoincrement) watch for changes to ensure latest spectrum is recent."""
        return await self.opcua.get_node(self.SAMPLE_COUNT).get_value()

    @staticmethod
    def _normalize_template_name(template_name) -> str:
        """Add `.iCIRTemplate` extension to string if not already present."""
        return (
            template_name
            if template_name.endswith(".iCIRTemplate")
            else template_name + ".iCIRTemplate"
        )

    @staticmethod
    def is_template_name_valid(template_name: str) -> bool:
        r"""Check template name validity. For the template folder location read below.

        From Mettler Toledo docs:
        You can use the Start method to create and run a new experiment in one of the iC analytical applications
        (i.e. iC IR, iC FBRM, iC Vision, iC Raman). Note that you must provide the name of an existing experiment
        template file that can be used as a basis for the new experiment.
        The template file must be located in a specific folder on the iC OPC UA Server computer.
        This is usually C:\\ProgramData\\METTLER TOLEDO\\iC OPC UA Server\\1.2\\Templates.
        """
        template_dir = Path(
            r"C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates",
        )
        if not template_dir.exists() or not template_dir.is_dir():
            logger.warning("iCIR template folder not found on the local PC!")
            return False

        # Ensures the name has been provided with no extension (common mistake)
        template_name = IcIR._normalize_template_name(template_name)

        return any(
            existing_tmpl.name == template_name
            for existing_tmpl in template_dir.glob("*.iCIRTemplate")
        )

    @staticmethod
    def parse_probe_info(probe_info_reply: str) -> ProbeInfo:
        """Convert the device reply into a ProbeInfo dictionary.

        Example probe_info_reply reply is:
        'FlowIR; SN: 2989; Detector: DTGS; Apodization: HappGenzel; IP Address: 192.168.1.2;
        Probe: DiComp (Diamond); SN: 14570173; Interface: FlowIR™ Sensor; Sampling: 4000 to 650 cm-1;
        Resolution: 8; Scan option: AutoSelect; Gain: 232;'
        """
        fields = probe_info_reply.split(";")
        probe_info = {
            "spectrometer": fields[0],
            "spectrometer_SN": fields[1].split(": ")[1],
            "probe_SN": fields[6].split(": ")[1],
        }

        # Use aliases, i.e. translate API names (left) to dict key (right)
        translate_attributes = {
            "Detector": "detector",
            "Apodization": "apodization",
            "IP Address": "ip_address",
            "Probe": "probe_type",
            "Sampling": "sampling_interval",
            "Resolution": "resolution",
            "Scan option": "scan_option",
            "Gain": "gain",
        }
        for element in fields:
            if ":" in element:
                piece = element.split(":")
                if piece[0].strip() in translate_attributes:
                    probe_info[translate_attributes[piece[0].strip()]] = piece[
                        1
                    ].strip()

        return ProbeInfo.model_validate(probe_info)

    @staticmethod
    async def _wavenumber_from_spectrum_node(node) -> list[float]:
        """Get the X-axis value of a spectrum. This is necessary as they change e.g. with resolution."""
        node_property = await node.get_properties()
        x_axis = await node_property[0].get_value()
        return x_axis.AxisSteps

    @staticmethod
    async def spectrum_from_node(node) -> IRSpectrum:
        """Given a Spectrum node returns it as IRSpectrum."""
        try:
            intensity = await node.get_value()
            wavenumber = await IcIR._wavenumber_from_spectrum_node(node)
            return IRSpectrum(wavenumber=wavenumber, intensity=intensity)

        except BadOutOfService:
            return IRSpectrum(wavenumber=[], intensity=[])

    async def last_spectrum_treated(self) -> IRSpectrum:
        """Return an IRSpectrum element for the last acquisition."""
        return await IcIR.spectrum_from_node(self.opcua.get_node(self.SPECTRA_TREATED))

    async def last_spectrum_raw(self) -> IRSpectrum:
        """RAW result latest scan."""
        return await IcIR.spectrum_from_node(self.opcua.get_node(self.SPECTRA_RAW))

    async def last_spectrum_background(self) -> IRSpectrum:
        """RAW result latest scan."""
        return await IcIR.spectrum_from_node(
            self.opcua.get_node(self.SPECTRA_BACKGROUND),
        )

    async def start_experiment(
        self,
        template: str,
        name: str = "Unnamed flowchem exp.",
    ):
        r"""Start an experiment on iCIR.

        Args:
        ----
            template: name of the experiment template, should be in the Templtates folder on the PC running iCIR.
                      That usually is C:\\ProgramData\\METTLER TOLEDO\\iC OPC UA Server\1.2\\Templates
            name: experiment name.
        """
        template = self._normalize_template_name(template)
        if self.is_local() and self.is_template_name_valid(template) is False:
            raise DeviceError(
                f"Cannot start template {template}: name not valid! Check if is in: "
                r'"C:\ProgramData\METTLER TOLEDO\iC OPC UA Server\1.2\Templates"'
            )
        if await self.probe_status() == "Running":
            logger.warning(
                "I was asked to start an experiment while a current experiment is already running!"
                "I will have to stop that first! Sorry for that :)",
            )
            # Stop running experiment and wait for the spectrometer to be ready
            await self.stop_experiment()
            await self.wait_until_idle()

        start_xp_nodeid = self.opcua.get_node(self.START_EXPERIMENT).nodeid
        method_parent = self.opcua.get_node(self.METHODS)
        try:
            # Collect_bg does not seem to work in automation, set to false and do not expose in start_experiment()!
            collect_bg = False
            await method_parent.call_method(start_xp_nodeid, name, template, collect_bg)
        except Bad as error:
            raise DeviceError(
                "The experiment could not be started!\n"
                "Check iCIR status and close any open experiment."
            ) from error
        logger.info(f"FlowIR experiment {name} started with template {template}!")
        return True

    async def stop_experiment(self):
        """Stop the experiment currently running.

        Note: the call does not make the instrument idle: you need to wait for the current scan to end!
        """
        method_parent = self.opcua.get_node(self.METHODS)
        stop_nodeid = self.opcua.get_node(self.STOP_EXPERIMENT).nodeid
        await method_parent.call_method(stop_nodeid)

    async def wait_until_idle(self):
        """Wait until no experiment is running."""
        while await self.probe_status() == "Running":
            await asyncio.sleep(0.2)


if __name__ == "__main__":
    ...

    async def main():
        template_name = "15_sec_integration.iCIRTemplate"
        url = IcIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS.replace(
            "localhost", "BSMC-YMEF002121"
        )
        ir_spectrometer = IcIR(template_name, url)

        if await ir_spectrometer.is_iCIR_connected():
            print("FlowIR connected!")
        else:
            raise ConnectionError("FlowIR not connected :(")

        await ir_spectrometer.start_experiment(
            name="reaction_monitoring", template=template_name
        )

        spectrum = await ir_spectrometer.last_spectrum_treated()
        while len(spectrum.intensity) == 0:
            spectrum = await ir_spectrometer.last_spectrum_treated()

        for x in range(3):
            spectra_count = await ir_spectrometer.sample_count()

            while await ir_spectrometer.sample_count() == spectra_count:
                await asyncio.sleep(1)

            print("New spectrum!")
            spectrum = await ir_spectrometer.last_spectrum_treated()
            print(spectrum)

        await ir_spectrometer.stop_experiment()

    asyncio.run(main())
