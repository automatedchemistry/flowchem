"""Bronkhorst El-flow mass flow controller (MFC) device driver."""
import asyncio

# Manufacturer package, see https://bronkhorst-propar.readthedocs.io/en/latest/introduction.html.
import propar
from loguru import logger

from flowchem import ureg
from flowchem.devices.bronkhorst.el_flow_component import EPCComponent, MFCComponent
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.utils.people import wei_hsin


def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False


class EPC(FlowchemDevice):
    """
    A class to represent an Electronic Pressure Controller (EPC) device from Bronkhorst.

    Attributes:
    -----------
    DEFAULT_CONFIG : dict
        Default configuration for the EPC device.
    port : str
        The port to which the EPC device is connected (Serial connection).
    channel : int
        The communication channel of the EPC device.
        Some instruments are a single node (one address) but contain multiple channels (for multiple sensors). To
        connect to a specific channel, specify the channel when creating an instrument instance. If no channel is
        specified the first channel will be used.
    address : int
        The address of the EPC device.
    max_pressure : float
        The maximum pressure of the EPC device in bar.
    id : str
        The identifier of the connected EPC device.

    Methods:
    --------
    initialize():
        Initialize the EPC device and set it to 0 bar.
    set_pressure(pressure: str):
        Set the pressure of the EPC device.
    get_pressure() -> float:
        Get the current pressure of the EPC device in bar.
    get_pressure_percentage() -> float:
        Get the current pressure of the EPC device as a percentage of the maximum pressure.
    """
    DEFAULT_CONFIG = {"channel": 1, "baudrate": 38400}  # "address": 0x80

    def __init__(
        self,
        port: str,
        name="",
        channel: int = 1,
        address: int = 0x80,
        max_pressure: float = 10,  # bar = 100 % = 32000
    ) -> None:
        """
        Constructs all the necessary attributes for the EPC object.

        Parameters:
        -----------
        port : str
            The port to which the EPC device is connected.
        name : str, optional
            The name of the EPC device (default is an empty string).
        channel : int, optional
            The communication channel of the EPC device (default is 1).        # Todo - explain better it
        address : int, optional
            The address of the EPC device (default is 0x80).                   # Todo - explain better it
        max_pressure : float, optional
            The maximum pressure of the EPC device in bar (default is 10).     # Todo - explain better it
        """
        self.port = port
        self.channel = channel
        self.address = address
        self.max_pressure = max_pressure
        super().__init__(name)

        # Metadata
        self.device_info.authors = [wei_hsin]
        self.device_info.manufacturer = "Bronkhorst"

        try:
            self.el_press = propar.instrument(
                self.port, address=self.address, channel=self.channel
            )
        except OSError as e:
            raise ConnectionError(f"Error connecting to {self.port} -- {e}") from e

        self.id = self.el_press.id
        logger.debug(f"Connected {self.id} to {self.port}")

    async def initialize(self):
        """Initialize the EPC device and set it to 0 bar."""
        await self.set_pressure("0 bar")
        self.components.append(EPCComponent("EPC", self))

    async def set_pressure(self, pressure: str):
        """
        Set the pressure setpoint of the EPC device.

        Parameters:
        -----------
        pressure : str
            The desired pressure to set. If no units are provided, bar is assumed.
        """
        if pressure.isnumeric() or isfloat(pressure):
            pressure = pressure + "bar"
            logger.warning("No units provided to set_pressure, assuming bar.")
        set_p = ureg.Quantity(pressure)
        set_n = round(set_p.m_as("bar") * 32000 / self.max_pressure)
        if set_n > 32000:
            self.el_press.setpoint = 32000
            logger.debug(
                "setting higher than maximum flow rate! set the flow rate to 100%",
            )
        else:
            self.el_press.setpoint = set_n
            logger.debug(f"set the pressure to {set_n / 320}%")

    async def get_pressure(self) -> float:
        """
        Get the current pressure of the EPC device in bar.

        Returns:
        --------
        float
            The current pressure in bar.
        """
        m_num = float(self.el_press.measure)
        return m_num / 32000 * self.max_pressure

    async def get_pressure_percentage(self) -> float:
        """
        Get the current pressure of the EPC device as a percentage of the maximum pressure.

        Returns:
        --------
        float
            The current pressure as a percentage of the maximum pressure.
        """
        m_num = float(self.el_press.measure)
        return m_num / 320


class MFC(FlowchemDevice):
    """
   A class to represent a Mass Flow Controller (MFC) device.

   Attributes:
   -----------
   DEFAULT_CONFIG : dict
       Default configuration for the MFC device.
   port : str
       The port to which the MFC device is connected.
   channel : int
       The communication channel of the MFC device.
   address : int
       The address of the MFC device.
   max_flow : float
       The maximum flow rate of the MFC device in ml/min.
   id : str
       The identifier of the connected MFC device.

   Methods:
   --------
   initialize():
       Ensure connection and initialize the MFC device.
   set_flow_setpoint(flowrate: str):
       Set the flow rate setpoint of the MFC device.
   get_flow_setpoint() -> float:
       Get the current flow rate of the MFC device in ml/min.
   get_flow_percentage() -> float:
       Get the current flow rate of the MFC device as a percentage of the maximum flow rate.
   """
    DEFAULT_CONFIG = {"channel": 1, "baudrate": 38400}  # "address": 0x80

    def __init__(
        self,
        port: str,
        name="",
        channel: int = 1,
        address: int = 0x80,
        max_flow: float = 9,  # ml / min = 100 % = 32000
    ) -> None:
        """
        Constructs all the necessary attributes for the MFC object.

        Parameters:
        -----------
        port : str
            The port to which the MFC device is connected.
        name : str, optional
            The name of the MFC device (default is an empty string).
        channel : int, optional
            The communication channel of the MFC device (default is 1).
        address : int, optional
            The address of the MFC device (default is 0x80).
        max_flow : float, optional
            The maximum flow rate of the MFC device in ml/min (default is 9).
        """
        self.port = port
        self.channel = channel
        self.address = address
        self.max_flow = max_flow
        super().__init__(name)
        self.max_flow = max_flow

        # Metadata
        self.device_info.model = "EL-FLOW"

        try:
            self.el_flow = propar.instrument(
                self.port, address=self.address, channel=self.channel
            )
        except OSError as e:
            raise ConnectionError(f"Error connecting to {self.port} -- {e}") from e
        self.id = self.el_flow.id
        logger.debug(f"Connected {self.id} to {self.port}")

    async def initialize(self):
        """Ensure connection and initialize the MFC device."""
        await self.set_flow_setpoint("0 ul/min")
        self.components.append(
            MFCComponent("MFC", self),
        )

    async def set_flow_setpoint(self, flowrate: str):
        """
        Set the flow rate setpoint of the MFC device in ml/min.

        Parameters:
        -----------
        flowrate : str
            The desired flow rate to set. If no units are provided, ml/min is assumed.
        """
        if flowrate.isnumeric() or isfloat(flowrate):
            flowrate = flowrate + "ml/min"
            logger.warning(
                "No units provided to set_flow_rate, assuming milliliter/minutes.",
            )

        set_f = ureg.Quantity(flowrate)
        set_n = round(set_f.m_as("ml/min") * 32000 / self.max_flow)
        if set_n > 32000:
            self.el_flow.setpoint = 32000
            logger.debug(
                "setting higher than maximum flow rate! set the flow rate to 100%",
            )
        else:
            self.el_flow.setpoint = set_n
            logger.debug(f"set the flow rate to {set_n / 320}%")

    async def get_flow_setpoint(self) -> float:
        """
        Get the current flow rate of the MFC device in ml/min.

        Returns:
        --------
        float
            The current flow rate in ml/min.
        """
        m_num = float(self.el_flow.measure)
        return m_num / 32000 * self.max_flow

    async def get_flow_percentage(self) -> float:
        """
        Get the current flow rate of the MFC device as a percentage of the maximum flow rate.

        Returns:
        --------
        float
            The current flow rate as a percentage of the maximum flow rate.
        """
        m_num = float(self.el_flow.measure)
        return m_num / 320


async def gas_flow(port: str, target_flowrate: str, reaction_time: float):
    Oxygen_flow = MFC(port, max_flow=10, address=6)
    await Oxygen_flow.initialize()
    await Oxygen_flow.set_flow_setpoint("900 ul/min")  # 10%
    # await asyncio.sleep(2)
    # for n in range(100):
    #     print(f"{n} time: {await Oxygen_flow.get_flow_setpoint()}%")
    #
    # # Oxygen_flow.set_flow_setpoint(target_point*32000/9.0)
    # # await asyncio.sleep(reaction_time*60)
    print(Oxygen_flow.id)
    await Oxygen_flow.set_flow_setpoint("0 ml/min")


async def mutiple_connect():
    flow = MFC("COM7", address=1, max_flow=10)
    EPC("COM7", address=2, max_pressure=10)
    MFC("COM7", address=6, max_flow=10)
    # O2_id = O2_flow.get_id
    # print(await pressure.get_id)
    # print(await flow.get_id)
    await flow.set_flow_setpoint("0.5")
    await flow.set_flow_setpoint("0")


def find_devices_info(port: str):
    """It is also possible to only create a master.
    This removes some abstraction offered by the instrument class,
    such as the setpoint and measure properties,
    the readParameter and writeParameter functions,
    and having to supply the node number on each read/write parameter call.
    """
    # Create the master
    master = propar.master(port, 38400)

    # Get nodes on the network
    nodes = master.get_nodes()

    # Read the usertag of all nodes
    for node in nodes:
        print(node)
        user_tag = master.read(node["address"], 113, 6, propar.PP_TYPE_STRING)
        print(user_tag)


if __name__ == "__main__":
    # find_devices_info("COM7")

    async def multiple_connect():
        flow = MFC("COM7", address=1, max_flow=10)
        pressure = EPC("COM7", address=2, max_pressure=10)
        O2_flow = MFC("COM7", address=6, max_flow=10)

        print(pressure.id)
        print(flow.id)
        print(O2_flow.id)

    asyncio.run(multiple_connect())

    db = propar.database()
    parameters = db.get_parameters([8, 9, 11, 142])
