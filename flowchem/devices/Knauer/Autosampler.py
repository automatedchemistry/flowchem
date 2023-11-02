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
    TCP_PORT = 2101
    BUFFER_SIZE = 1024

    def __init__(self, ip_address, buffersize=None, udp_port=None):
        self.ip_address = str(ip_address)
        self.port = udp_port if udp_port else ASEthernetDevice.TCP_PORT
        self.buffersize = buffersize if buffersize else ASEthernetDevice.BUFFER_SIZE

        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=logging.DEBUG,
        )

    def _send_and_receive(self, message: str):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.ip_address, self.port))

                s.send(message.encode())
                reply = b""
                while True:
                    chunk = s.recv(1024)
                    reply += chunk
                    if chunk in NDA_knauer_AS.knauer_AS.CommunicationFlags.__dict__.values() or NDA_knauer_AS.knauer_AS.ReplyStructure.MESSAGE_END.value in chunk:
                        break
            return reply
        except socket.timeout:
            logging.error(f"No connection possible to device with IP {self.ip_address}")
            raise ConnectionError(
                f"No Connection possible to device with ip_address {self.ip_address}"
            )


class KnauerAS(ASEthernetDevice):
    """
    Class to control Knauer or basically any Spark Holland AS.

    """
    AS_ID = 61
    def __init__(self,ip_address,  autosampler_id = None, port=ASEthernetDevice.TCP_PORT, buffersize=ASEthernetDevice.BUFFER_SIZE):

        super().__init__(ip_address, buffersize, port)
        # get statuses, that is basically syringe syize, volumes, platetype

        self.autosampler_id = autosampler_id if autosampler_id else KnauerAS.AS_ID

    def autosampler_set(self, message: str or int):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = self._send_and_receive(message)

        # this only checks that it was acknowledged
        self._parse_setting_reply(reply)

    def autosampler_query(self, message: str or int):
        """
        Sends command and receives reply, deals with all communication based stuff and checks that the valve is
        of expected type
        :param message:
        :return: reply: str
        """
        reply = self._send_and_receive(message)

        query_reply = self._parse_query_reply(reply, message)
        return query_reply

    def _parse_setting_reply(self, reply):
        # reply needs to be binary string
        from NDA_knauer_AS.knauer_AS import CommunicationFlags

        if reply == CommunicationFlags.ACKNOWLEDGE:
            return True
        elif reply == CommunicationFlags.TRY_AGAIN:
            raise ASBusyError
        elif reply == CommunicationFlags.NOT_ACKNOWLEDGE:
            raise CommandOrValueError
        # this is only the case with replies on queries
        else:
            raise ASError(f"The reply is {reply} and does not fit the expected reply for value setting")

    def _parse_query_reply(self, reply, as_command):
        from NDA_knauer_AS.knauer_AS import ReplyStructure, KnauerASCommands
        reply_start_char, reply_stripped, reply_end_char = reply[:ReplyStructure.STX_END.value], \
                                                           reply[
                                                           ReplyStructure.STX_END.value:ReplyStructure.ETX_START.value], \
                                                           reply[ReplyStructure.ETX_START.value:]
        if reply_start_char != ReplyStructure.MESSAGE_START | reply_end_char != ReplyStructure.MESSAGE_END:
            raise CommunicationError


        # basically, if the device gives an extended reply, length will be 14. This only matters for get commands
        if len(reply_stripped) == 14:
        # decompose further
            as_id = reply_stripped[ReplyStructure.STX_END.value:ReplyStructure.ID_END.value]
            as_ai = reply_stripped[ReplyStructure.ID_END.value:ReplyStructure.AI_END.value]
            as_pfc = reply_stripped[ReplyStructure.AI_END.value:ReplyStructure.PFC_END.value]
            as_val = reply_stripped[ReplyStructure.PFC_END.value:ReplyStructure.VALUE_END.value]
            # check if reply from requested device
            if as_id.decode() != self.autosampler_id:
                raise ASError(f"ID of used AS is {self.autosampler_id}, but ID in reply is as_id")
            if as_pfc.decode() != as_command[ReplyStructure.AI_END.value:ReplyStructure.PFC_END.value]:
                raise ASError(f"Reply of AS is for another query. Query was {KnauerASCommands[as_command].name}, but reply is for {KnauerASCommands[as_pfc].name}")
            return as_val.decode().lstrip("0")
            # check the device ID against current device id, check that reply is on send request

        else:
            raise ASError(f"AS reply did not fit any of the known patterns, reply is: {reply_stripped}")






if __name__ == "__main__":
    pass