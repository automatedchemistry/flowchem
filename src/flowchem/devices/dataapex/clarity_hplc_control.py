from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Query

from flowchem.components.analytics.hplc import HPLCControl

if TYPE_CHECKING:
    from flowchem.devices import Clarity


class ClarityComponent(HPLCControl):
    """
    A component for controlling a ClarityChrom system with HPLC functionality.

    This class extends HPLCControl and adds ClarityChrom-specific functionality, such as starting and stopping the ClarityChrom instance and sending methods or running samples.

    Attributes:
    -----------
    hw_device : Clarity
        The ClarityChrom hardware device this component interfaces with.

    Methods:
    --------
    exit() -> bool:
        Exit the ClarityChrom application.
    send_method(method_name: str) -> bool:
        Set the HPLC method using a file with a .MET extension.
    run_sample(sample_name: str, method_name: str) -> bool:
        Run an analysis on the instrument with the specified sample and method.
    """

    hw_device: Clarity  # for typing's sake

    def __init__(self, name: str, hw_device: Clarity) -> None:
        """
        Constructs all the necessary attributes for the ClarityComponent object.

        Parameters:
        -----------
        name : str
            The name of the Clarity component.
        hw_device : Clarity
            The ClarityChrom hardware device this component interfaces with.
        """
        super().__init__(name, hw_device)
        # Clarity-specific command
        self.add_api_route("/exit", self.exit, methods=["PUT"])

    async def exit(self) -> bool:
        """
        Exit the ClarityChrom application.

        Returns:
        --------
        bool
            True if the exit command was successfully executed, False otherwise.
        """
        return await self.hw_device.execute_command("exit", without_instrument_num=True)

    async def send_method(
        self,
        method_name: str = Query(
            default=...,
            description="Name of the method file",
            examples=["MyMethod.MET"],
            alias="method-name",
        ),
    ) -> bool:
        """
        Set the HPLC method using a file with a .MET extension.

        Ensure that the 'Send Method to Instrument' option is selected in the Method Sending Options dialog in
        System Configuration.

        Parameters:
        -----------
        method_name : str
            The name of the method file to be sent.

        Returns:
        --------
        bool
            True if the method was successfully sent, False otherwise.
        """
        return await self.hw_device.execute_command(f" {method_name}")

    async def run_sample(
        self,
        sample_name: str = Query(
            default=...,
            description="Sample name",
            examples=["JB-123-crude-2h"],
            alias="sample-name",
        ),
        method_name: str = Query(
            default=...,
            description="Name of the method file",
            examples=["MyMethod.MET"],
            alias="method-name",
        ),
    ) -> bool:
        """
        Run an analysis on the instrument with the specified sample and method.

        Note that it takes at least 2 sec until the run actually starts (depending on instrument configuration).
        While the export of the chromatogram in e.g. ASCII format can be achieved programmatically via the CLI, the best
        solution is to enable automatic data export for all runs of the HPLC as the chromatogram will be automatically
        exported as soon as the run is finished.

        Parameters:
        -----------
        sample_name : str
            The name of the sample to be run.
        method_name : str
            The name of the method file to be used.

        Returns:
        --------
        bool
            True if the sample was successfully run, False otherwise.
        """
        if not await self.hw_device.execute_command(f'set_sample_name="{sample_name}"'):
            return False
        if not await self.send_method(method_name):
            return False
        return await self.hw_device.execute_command(
            f"run={self.hw_device.instrument}",
            without_instrument_num=True,
        )
