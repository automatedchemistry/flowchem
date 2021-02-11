# This could become a mess...
# what needs to be done is switch the lamps on, which works over serial.
# the rest is just sending commands to the console, possibly also to another machine
import tenacity
import subprocess
import socket
from threading import Thread
from typing import Union
from time import sleep
from pathlib import Path


class ClarityInterface:
    def __init__(self, remote: bool = False, host: str = None, port: int = None, path_to_executable: str = None,
                 instrument_number: int = 1):
        # just determine path to executable, and open socket if for remote usage
        self.remote = remote
        self.instrument = instrument_number
        self.path_to_executable = path_to_executable
        if self.remote:
            self.interface = MessageSender(host, port)
            self.command_executor = self.interface.open_socket_and_send
        else:
            self.command_executor = ClarityExecutioner.execute_command

    # if remote execute everything on other PC, else on this

    def execute_command(self, command_string):
        if self.remote:
            self.command_executor(command_string)
        else:
            self.command_executor(self.command_executor, command_string, self.path_to_executable)

    # bit displaced convenience function to switch on the lamps of hplc detector. Careful, NDA
    # TODO remove if published
    def switch_lamp_on(self, address='192.168.10.107', port=10001):
        # send the  respective two commands and check return. Send to socket
        message_sender=MessageSender(address, port)
        message_sender.open_socket_and_send('LAMP_D2 1\n\r')
        sleep(0.1)
        message_sender.open_socket_and_send('LAMP_HAL 1\n\r')

    # define relevant strings
    def open_clarity_chrom(self, user: str, password: str = None):
        if not password:
            self.execute_command(f"i={self.instrument} u={user}")
        else:
            self.execute_command(f"i={self.instrument} u={user} p={password}")

    def load_file(self, path_to_file: str):
        """has to be done to open project, then method. Take care to select 'Send Method to Instrument' option in Method
         Sending Options dialog in System Configuration."""
        self.execute_command(f"i={self.instrument} {path_to_file}")

    def set_sample_name(self, sample_name):
        """Sets the sample name for the next single run"""
        self.execute_command(f"i={self.instrument} set_sample_name={sample_name}")

    def run(self):
        """Runs the instrument. Care should be taken to activate automatic data export on HPLC. (can be done via command,
         but that only makes it more complicated). Takes at least 2 sec until run starts"""
        self.execute_command(f'run={self.instrument}')


class MessageSender:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    # encode('utf-8')

    @tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(2), reraise=True)
    def open_socket_and_send(self, message: str):
        s = socket.socket()
        s.connect((self.host, self.port))
        s.sendall(message.encode('utf-8'))
        s.close()


class ClarityExecutioner:
    """ This needs to run on the computer having claritychrom installed, except for one uses the same PC. However,
    going via socket and localhost would also work, but seems a bit cumbersome.
    open up server socket. Everything coming in will be prepended with claritychrom.exe (if it is not already)"""
    command_prepend = 'claritychrom.exe'

    def __init__(self, port, allowed_client='192.168.10.20', host_ip='192.168.10.11'):
        self.port = port
        self.allowed_client = allowed_client
        self.host_ip = host_ip
        # think that should also go in thread, otherwise blocks
        self.server_socket = self.open_server()
        self.executioner = Thread(target=self.get_commands_and_execute, daemon=True)
        self.executioner.start()

    def open_server(self):
        s = socket.socket()
        s.bind((self.host_ip, self.port))
        s.listen(5)
        return s

    def accept_new_connection(self):
        client_socket, address = self.server_socket.accept()
        if not address[0] == self.allowed_client:
            client_socket.close()
            print(f'nice try {client_socket, address}')
        else:
            # if below code is executed, that means the sender is connected
            print(f"[+] {address} is connected.")
            # in unicode
            request = client_socket.recv(1024).decode('utf-8')
            client_socket.close()
            print(request)
            return request

    def execute_command(self, command: str, folder_of_executable: Union[Path, str] = r'C:\claritychrom\bin\\'):
        prefix = 'claritychrom.exe'
        # sanitize input a bit
        if command.split(' ')[0] != prefix:
            command = folder_of_executable + prefix + ' ' + command
            print(command)
        try:
            x = subprocess.run(command, shell=True, capture_output=False, timeout=3)
        except subprocess.TimeoutExpired:
            print('Damn, Subprocess')

    def get_commands_and_execute(self):
        while True:
            request=self.accept_new_connection()
            self.execute_command(request)
            sleep(1)
