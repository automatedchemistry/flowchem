"""
Module for communication with Autosampler.
"""

# For future: go through graph, acquire mac addresses, check which IPs these have and setup communication.
# To initialise the appropriate device on the IP, use class name like on chemputer


import logging
import socket
import time

import NDA_knauer_AS.knauer_AS
from NDA_knauer_AS import *

try:
    # noinspection PyUnresolvedReferences
    from NDA_knauer_AS import *

    HAS_AS_COMMANDS = True
except ImportError:
    HAS_AS_COMMANDS = False

# from pint import UnitRegistry
# finding the AS is not trivial with autodiscover, it also only is one device


class ASError(Exception):
    pass


class CommunicationError(ASError):
    """Command is unknown, value is unknown or out of range, transmission failed"""
    pass


class CommandOrValueError(ASError):
    """Command is unknown, value is unknown or out of range, transmission failed"""
    pass


class ASBusyError(ASError):
    """AS is currently busy but will accept your command at another point of time"""
    pass


#TODO do not decode reply before digestion, leave in binary
class ASEthernetDevice:
    UDP_PORT = 2101
    BUFFER_SIZE = 1024

    def __init__(self, ip_address, buffersize=None, udp_port=None):
        self.ip_address = str(ip_address)
        self.port = udp_port if udp_port else ASEthernetDevice.UDP_PORT
        self.buffersize = buffersize if buffersize else ASEthernetDevice.BUFFER_SIZE

        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=logging.DEBUG,
        )

    def _open_and_send(self, message: str):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(5)
                s.connect((self.ip_address, self.port))
                print("connected")
                s.send(message.encode())

        except socket.timeout:
            logging.error(f"No connection possible to device with IP {self.ip_address}")
            raise ConnectionError(
                f"No Connection possible to device with ip_address {self.ip_address}"
            )

    def _open_and_receive(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(5)
                s.bind(("", self.port))
                reply = s.recv(1024).decode()

        except socket.timeout:
            logging.error(f"No reply received from device with IP {self.ip_address}")
            raise ConnectionError(
                f"No reply received from device with ip_address {self.ip_address}"
            )

        return reply

    def _send_and_receive(self, message):
        # send hex encoded string
        self._open_and_send(message)
        reply = self._open_and_receive()
        return reply


class KnauerAS(ASEthernetDevice):
    """
    Class to control Knauer or basically any Spark Holland AS.

    """

    def __init__(self, ip_address, port=ASEthernetDevice.UDP_PORT, buffersize=ASEthernetDevice.BUFFER_SIZE):

        super().__init__(ip_address, port, buffersize)
        # get statuses, that is basically syringe syize, volumes, platetype

    def communicate(self, message: str):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = super()._send_and_receive(message)
        # reply digest

        # verify that reply start and end are alright

        # verify that reply is present in
        if reply in NDA_knauer_AS.knauer_AS.ASReplies:
            # retry once

            if reply == NDA_knauer_AS.knauer_AS.ASReplies.NOT_ACKNOWLEDGE:
                ASError()
        elif 1:
            # do true message digest
            pass
        else:
            # message is neither simple reply nor an extended one -> bullshit reply
            raise ASError
            pass
            return reply

    def get_current_position(self):
        curr_pos = self.communicate("P")
        logging.debug(f"Current position is {curr_pos}")

        return curr_pos

    def switch_to_position(self, position: int or str):
        try:
            position = int(position)
        except ValueError:
            pass

        # allows lower and uppercase commands in case of injection
        if isinstance(position, str):
            position = position.upper()

        # switching necessary?
        if position == self._valve_state:
            logging.debug("already at that position")
            return

        # change to selected position
        reply = self.communicate(position)

        # check if this was done
        if reply == "OK":
            logging.debug("switching successful")
            self._valve_state = position

        elif "E0" in reply:

            logging.error("valve was not switched because valve refused")
            raise SwitchingException("valve was not switched because valve refused")

        elif "E1" in reply:
            logging.error("Motor current to high. Check that")
            raise SwitchingException("Motor current to high. Check that")

        else:
            raise SwitchingException(f"Unknown reply received. Reply is {reply}")

    def get_valve_type(self):
        """aquires valve type, if not supported will throw error.
        This also prevents to initialize some device as a KnauerValve"""
        reply = self.communicate("T")[6:]
        # could be more pretty by passing expected answer to communicate
        try:
            reply = int(reply)
        except ValueError:
            pass
        try:
            headtype = KnauerValveHeads(reply)
        except ValueError as e:
            raise KnauerError(
                f"It seems you're trying instantiate a unknown device/unknown valve type {e} as Knauer Valve."
                "Only Valves of type 16, 12, 10 and LI are supported"
            ) from e
        logging.info(
            f"Valve successfully connected, Type is {headtype} at address {self.ip_address}"
        )
        return headtype

    def close_connection(self):
        logging.info(f"Valve at address closed connection {self.ip_address}")
        self.sock.close()


# Read and write, read: command?; write = command:setpoint
# BEWARE MANUAL STATES 0-50000µml/min HOWEVER this depends on headtype
FLOW = "FLOW"  # 0-50000 µL/min, int only!
PMIN10 = "PMIN10"  # 0-400 in 0.1 MPa, use to avoid dryrunning
PMIN50 = "PMIN50"  # 0-150 in 0.1 MPa, use to avoid dryrunning
PMAX10 = "PMAX10"  # 0-400 in 0.1 MPa, chosen automatically by selecting pump head
PMAX50 = "PMAX50"  # 0-150 in 0.1 MPa, chosen automatically by selecting pumphead
IMIN10 = "IMIN10"  # 0-100 minimum motor current
IMIN50 = "IMIN50"  # 0-100 minimum motor current
HEADTYPE = "HEADTYPE"  # 10, 50 ml. Value refers to highest flowrate in ml/min
STARTLEVEL = "STARTLEVEL"  # 0, 1 configures start. 0 -> only start pump when shorted to GND, 1 -> always allow start
ERRIO = "ERRIO"  # 0, 1 write/read error in/output ??? sets errio either 1 or 0, reports errio:ok
STARTMODE = "STARTMODE"  # 0, 1; 0=pause pump after switchon, 1=start immediatley with previous set flow rate
# no idea what these do...
ADJ10 = "ADJ10"  # 100-2000
ADJ50 = "ADJ50"  # 100-2000
CORR10 = "CORR10"  # 0-300
CORR50 = "CORR50"  # 0-300

# RD only
EXTFLOW = "EXTFLOW?"
IMOTOR = "IMOTOR?"  # motor current in relative units 0-100
PRESSURE = "PRESSURE?"  # reads the pressure in 0.1 MPa
ERRORS = "ERRORS?"  # displays last 5 error codes

# WR only
EXTCONTR = (
    "EXTCONTR:"  # 0, 1; 1= allows flow control via external analog input, 0 dont allow
)
LOCAL = "LOCAL"  # no parameter, releases pump to manual control
REMOTE = "REMOTE"  # manual param input prevented
PUMP_ON = "ON"  # starts flow
PUMP_OFF = "OFF"  # stops flow


class KnauerPump(KnauerEthernetDevice):
    def __init__(
        self,
        ip_address,
        port=None,
        buffersize=None,
    ):
        super().__init__(ip_address, port, buffersize)
        self.max_pressure, self.max_flow = None, None
        # Check connection by reading pump head type
        _ = self.headtype

    def communicate(self, message: str):
        """
        sends command and receives reply, deals with all communication based stuff and checks
        that the valve is of expected type
        :param message:
        :return: reply: str
        """

        # beware: I think the pumps want \n\r as end of message, the valves \r\n
        message = str(message) + "\n\r"
        reply = super()._send_and_receive_handler(message).rstrip()
        if "ERROR:1" in reply:
            CommandError(
                f"Invalid message sent to device. Message was: {message}. Reply is {reply}"
            )

        elif "ERROR:2" in reply:
            ParameterError(
                f"Setpoint refused by device. Refer to manual for allowed values.  Message was: '{message}'. "
                f"Reply is '{reply}'"
            )

        elif ":OK" in reply:
            logging.info("setpoint successfully set")

        elif message.rstrip()[:-1] + ":" in reply:
            logging.info(f"setpoint successfully acquired, is {reply}")
            return reply.split(":")[-1]
        elif not reply:
            raise CommandError("No reply received")
        return reply

    # read and write. write: append ":value", read: append "?"
    def message_constructor_dispatcher(
        self, message, setpoint: int = None, setpoint_range: tuple = None
    ):

        if not setpoint:
            return self.communicate(message + "?")

        elif setpoint_range:
            if setpoint in range(*setpoint_range):
                return self.communicate(message + ":" + str(setpoint))

            else:
                ParameterError(
                    f"Internal check shows that setpoint provided ({setpoint}) is not in range ({setpoint_range})."
                    f"Refer to manual."
                )

        else:
            return self.communicate(message + ":" + str(setpoint))

    def set_flow(self, setpoint_in_ml_min: float = None):
        """

        :param setpoint_in_ml_min: in mL/min
        :return: nothing
        """
        set_flowrate_ul_min = int(setpoint_in_ml_min * 1000)
        flow = self.message_constructor_dispatcher(FLOW, setpoint=set_flowrate_ul_min,
            setpoint_range=(0, self.max_flow + 1),
        )
        logging.info(
            f"Flow of pump {self.ip_address} is set to {setpoint_in_ml_min}, returns {flow}"
        )

    @property
    def headtype(self):
        reply = int(self.message_constructor_dispatcher(HEADTYPE)[-2:])
        try:
            headtype = KnauerPumpHeads(reply)
        except ValueError as e:
            raise KnauerError(
                "It seems you're trying instantiate an unknown device/unknown pump type as Knauer Pump."
                "Only Knauer Azura Compact is supported"
            ) from e

        logging.info(f"Head type of pump {self.ip_address} is {headtype}")
        self.max_pressure, self.max_flow = (
            (400, 10000)
            if headtype == KnauerPumpHeads.FLOWRATE_TEN_ML
            else (150, 50000)
        )
        return headtype

    @headtype.setter
    def headtype(self, setpoint: KnauerPumpHeads):
        reply = self.message_constructor_dispatcher(HEADTYPE, setpoint=setpoint.value)
        self.max_pressure, self.max_flow = (
            (400, 10000)
            if setpoint == KnauerPumpHeads.FLOWRATE_TEN_ML
            else (150, 50000)
        )
        logging.info(
            f"Head type of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    def set_minimum_pressure(self, pressure_in_bar=None):

        command = PMIN10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMIN50

        reply = self.message_constructor_dispatcher(
            command,
            setpoint=pressure_in_bar,
            setpoint_range=(0, self.max_pressure + 1),
        )

        logging.info(
            f"Minimum pressure of pump {self.ip_address} is set to {pressure_in_bar}, returns {reply}"
        )

    def set_maximum_pressure(self, pressure_in_bar=None):
        command = PMAX10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else PMAX50

        reply = self.message_constructor_dispatcher(
            command,
            setpoint=pressure_in_bar,
            setpoint_range=(0, self.max_pressure + 1),
        )

        logging.info(
            f"Maximum pressure of pump {self.ip_address} is set to {pressure_in_bar}, returns {reply}"
        )

    def set_minimum_motor_current(self, setpoint=None):
        command = IMIN10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else IMIN50

        reply = self.message_constructor_dispatcher(
            command, setpoint=setpoint, setpoint_range=(0, 101)
        )
        logging.info(
            f"Minimum motor current of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    def set_start_level(self, setpoint=None):
        reply = self.message_constructor_dispatcher(
            STARTLEVEL, setpoint=setpoint, setpoint_range=(0, 2)
        )
        logging.info(
            f"Start level of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    def set_start_mode(self, setpoint=None):
        """

        :param setpoint: 0 pause pump after switch on. 1 switch on immediately with previously selected flow rate
        :return: device message
        """
        if setpoint in (0, 1):
            reply = self.message_constructor_dispatcher(STARTMODE, setpoint=setpoint)
            logging.info(
                f"Start mode of pump {self.ip_address} is set to {setpoint}, returns {reply}"
            )
        else:
            logging.warning("Supply binary value")

    def set_adjusting_factor(self, setpoint: int = None):
        command = ADJ10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else ADJ50
        reply = self.message_constructor_dispatcher(
            command, setpoint=setpoint, setpoint_range=(0, 2001)
        )
        logging.info(
            f"Adjusting factor of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    def set_correction_factor(self, setpoint=None):
        command = CORR10 if self.headtype == KnauerPumpHeads.FLOWRATE_TEN_ML else CORR50
        reply = self.message_constructor_dispatcher(
            command, setpoint=setpoint, setpoint_range=(0, 301)
        )
        logging.info(
            f"Correction factor of pump {self.ip_address} is set to {setpoint}, returns {reply}"
        )

    # read only
    def read_pressure(self):
        reply = int(self.communicate(PRESSURE))
        logging.info(f"Pressure reading of pump {self.ip_address} returns {reply} bar")
        return reply

    def read_extflow(self):
        reply = int(self.communicate(EXTFLOW))
        logging.info(f"Extflow reading of pump {self.ip_address} returns {reply}")
        return reply

    def read_errors(self):
        reply = self.communicate(ERRORS)
        logging.info(f"Error reading of pump {self.ip_address} returns {reply}")
        return reply

    def read_motor_current(self):
        reply = int(self.communicate(IMOTOR))
        logging.info(f"Motor current reading of pump {self.ip_address} returns {reply} A")
        return reply

    # TODO run flag
    # write only
    def start_flow(self):
        self.communicate(PUMP_ON)
        logging.info("Pump switched on")

    def stop_flow(self):
        self.communicate(PUMP_OFF)
        logging.info("Pump switched off")

    def set_local(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set local {param}")
            self.communicate(LOCAL + ":" + str(param))
        else:
            logging.warning("Supply binary value")

    def set_remote(self, param: int):
        if param in (0, 1):
            logging.info(f"Pump {self.ip_address} set remote {param}")
            self.communicate(REMOTE + ":" + str(param))
        else:
            logging.warning("Supply binary value")






if __name__ == "__main__":
    pass