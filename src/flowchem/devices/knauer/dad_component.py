"""Knauer DAD component."""
from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.sensors.photo_sensor import PhotoSensor

if TYPE_CHECKING:
    from flowchem.devices.knauer.dad import KnauerDAD
from flowchem.components.technical.power import PowerSwitch


class KnauerDADLampControl(PowerSwitch):
    """
    Control the lamp of the Knauer DAD device.

    Attributes:
        hw_device (KnauerDAD): The hardware device for the Knauer DAD.
    """
    hw_device: KnauerDAD

    def __init__(self, name: str, hw_device: KnauerDAD) -> None:
        """
        Initialize the KnauerDADLampControl component.

        Args:
            name (str): The name of the component.
            hw_device (KnauerDAD): The hardware device instance for controlling the Knauer DAD lamp.
        """
        super().__init__(name, hw_device)
        self.lamp = name
        self.add_api_route("/lamp_status", self.get_lamp, methods=["GET"])
        self.add_api_route("/status", self.get_status, methods=["GET"])

    async def get_status(self) -> str:
        """
        Get the status of the instrument.

        Returns:
            str: The status of the instrument.
        """
        return await self.hw_device.status()

    async def get_lamp(self):
        """
        Get the status of the lamp.

        Returns:
            str: The status of the lamp.
        """
        return await self.hw_device.lamp(self.lamp)
        # return {

    async def power_on(self):
        """
        Turn the lamp power on.

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.lamp(self.lamp, "ON")

    async def power_off(self):
        """
        Turn the lamp power off.

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.lamp(self.lamp, "OFF")

    async def set_lamp(self, state: str) -> str:
        """
        Set the lamp state.

        Args:
            state (str): The desired state of the lamp ("ON" or "OFF").

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.lamp(self.lamp, state)
        # match lamp_name:
        #     case "d2":
        #         await self.hw_device.d2(state)
        #     case "hal":
        #         await self.hw_device.hal(state)
        #     case _:
        #         logger.error("unknown lamp name!")


class DADChannelControl(PhotoSensor):
    """
    Control a specific channel of the Knauer DAD device.

    Attributes:
        hw_device (KnauerDAD): The hardware device for the Knauer DAD.
        channel (int): The channel number to control.
    """
    hw_device: KnauerDAD

    def __init__(self, name: str, hw_device: KnauerDAD, channel: int) -> None:
        """
        Initialize the DADChannelControl component.

        Args:
            name (str): The name of the component.
            hw_device (KnauerDAD): The hardware device instance for controlling the Knauer DAD channel.
            channel (int): The channel number to control.
        """
        super().__init__(name, hw_device)
        self.channel = channel

        # additional parameters
        self.add_api_route("/set-wavelength", self.set_wavelength, methods=["PUT"])
        self.add_api_route(
            "/set-integration-time",
            self.set_integration_time,
            methods=["PUT"],
        )
        self.add_api_route("/set-bandwidth", self.set_bandwidth, methods=["PUT"])

        # Ontology: diode array detector
        self.component_info.owl_subclass_of.append(
            "http://purl.obolibrary.org/obo/CHMO_0002503",
        )

    async def acquire_signal(self) -> float:
        """
        Acquire a signal from the sensor.

        Returns:
            float: The acquired signal.
        """
        return await self.hw_device.read_signal(self.channel)

    async def set_wavelength(self, wavelength: int):
        """
        Set the acquisition wavelength.

        Be aware that wavelength=0 means that nothing will be collected.

        Args:
            wavelength (int): The desired wavelength in nm (0-999 nm).

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.set_wavelength(self.channel, wavelength)

    async def set_integration_time(self, int_time: int):
        """
        Set the integration time.

        Args:
            int_time (int): The desired integration time in ms (10 - 2000 ms).

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.integration_time(int_time)

    async def set_bandwidth(self, bandwidth: int):
        """
        Set the bandwidth.

        Args:
            bandwidth (int): The desired bandwidth in nm (4 to 25 nm).

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.bandwidth(bandwidth)

    async def set_shutter(self, status: str): # Todo: Not used
        """
        Set the shutter status.

        Args:
            status (str): The desired shutter status ("CLOSED", "OPEN", or "FILTER").

        Returns:
            str: The response from the hardware device.
        """
        return await self.hw_device.shutter(status)

    async def power_on(self) -> str:
        """
        Check the lamp status.

        Returns:
            str: The status of both the D2 and halogen lamps.
        """
        return f"d2 lamp is {await self.hw_device.lamp('d2')}; halogen lamp is {await self.hw_device.lamp('hal')}"

    async def power_off(self) -> str:
        """
        Deactivate the measurement channel.

        Returns:
            str: The response from the hardware device.
        """
        reply = await self.hw_device.set_wavelength(self.channel, 0)
        return reply
