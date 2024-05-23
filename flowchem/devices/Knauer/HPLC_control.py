# This could become a mess...
# what needs to be done is switch the lamps on, which works over serial.
# the rest is just sending commands to the console, possibly also to another machine

#https://www.dataapex.com/documentation/Content/Help/110-technical-specifications/110.020-command-line-parameters/110.020-command-line-parameters.htm?Highlight=command%20line

import tenacity
import subprocess
import socket
from threading import Thread
from typing import Union
from time import sleep
from pathlib import Path

# Todo should have a command constructor dataclass, would be more neat. For now, will do without to get it running asap

# TODO Verz weird, when starting from synthesis, fractioning valve is blocked. no idea why, it's ip is not used.

class ClarityInterface:
    def __init__(self, remote: bool = False, host: str = None, port: int = None, path_to_executable: str = None,
                 instrument_number: int = 1, execute: bool = True):
        # just determine path to executable, and open socket if for remote usage
        self.remote = remote
        self.instrument = instrument_number
        self.path_to_executable = path_to_executable
        self._execute = execute
        if self.remote:
            self.interface = MessageSender(host, port)
            self.command_executor = self.interface.open_socket_and_send
        else:
            self.command_executor = ClarityExecutioner.execute_command

    # if remote execute everything on other PC, else on this
    # Todo doesn't make sense here, done other way
    def execute_command(self, command_string):
        if self._execute:
            if self.remote:
                self.command_executor(command_string)
            else:
                self.command_executor(command_string, self.path_to_executable)
        else:
            print(f"Command {command_string} would have been executed")
        
    #bit displaced convenience function to switch on the lamps of hplc detector. Careful, NDA
    # TODO remove if published
    def switch_lamp_on(self, address='192.168.10.111', port=10001):
        """
        Has to be performed BEFORE starting clarity, otherwise sockets get blocked
        Args:
            address:
            port:

        Returns:

        """
        # send the  respective two commands and check return. Send to socket
        message_sender=MessageSender(address, port)
        message_sender.open_socket_and_send('LAMP_D2 1\n\r')
        sleep(1)
        message_sender.open_socket_and_send('LAMP_HAL 1\n\r')
        sleep(15)

    # define relevant strings
    def open_clarity_chrom(self, user: str,  config_file: str, password: str = None, start_method: str = ''):
        """
        start_method: supply the path to the method to start with, this is important for a soft column start
        config file: if you want to start with specific instrumment configuration, specify location of config file here
        """
        if not password:
            self.execute_command(f"disable_message_boxes cfg={config_file} i={self.instrument} u={user} {start_method}")
        else:
            self.execute_command(f"disable_message_boxes cfg={config_file} i={self.instrument} u={user} p={password} {start_method}")
        sleep(20)

    # TODO should be OS agnostic
    def slow_flowrate_ramp(self, path: str, method_list: tuple = ()):
        """
        path: path where the methods are located
        method list
        """
        for current_method in method_list:
            self.execute_command(f"i={self.instrument} {path}\\{current_method}")
            # not very elegant, but sending and setting method takes at least 10 seconds, only has to run during platform startup and can't see more elegant way how to do that
            sleep(20)


    def load_file(self, path_to_file: str):
        """has to be done to open project, then method. Take care to select 'Send Method to Instrument' option in Method
         Sending Options dialog in System Configuration."""
        self.execute_command(f"i={self.instrument} {path_to_file}")
        sleep(10)

    def set_sample_name(self, sample_name):
        """Sets the sample name for the next single run"""
        self.execute_command(f"i={self.instrument} set_sample_name={sample_name}")
        sleep(1)

    def run(self):
        """Runs the instrument. Care should be taken to activate automatic data export on HPLC. (can be done via command,
         but that only makes it more complicated). Takes at least 2 sec until run starts"""
        self.execute_command(f'run={self.instrument}')

    def exit(self):
        """Exit Clarity Chrom"""
        self.execute_command('exit')
        sleep(10)



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
        self.executioner = Thread(target=self.get_commands_and_execute, daemon=False)
        print('a')
        self.executioner.start()
        print('b')

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


    # TODO: instrument number has to go into command execution
    def execute_command(self, command: str, folder_of_executable: Union[Path, str] = r'C:\claritychrom\bin\\'):
        prefix = 'claritychrom.exe'
        # sanitize input a bit
        if command.split(' ')[0] != prefix:
            command = folder_of_executable + prefix + ' ' + command
            print(command)
        try:
            x = subprocess
            x.run(command, shell=True, capture_output=False, timeout=3)
        except x.TimeoutExpired:
            print('Damn, Subprocess')

    def get_commands_and_execute(self):
        while True:
            request=self.accept_new_connection()
            self.execute_command(request)
            sleep(1)
            print('listening')

###TODO: also dsk or k for opening with specific desktop could be helpful-.
# TODO Export results can be specified -> exports result, rewrite to a nicer interface

if __name__ == "__main__":
    computer_w_Clarity = False
    if computer_w_Clarity  == True:
        analyser = ClarityExecutioner(10014)
    elif computer_w_Clarity == False:
        commander = ClarityInterface(remote=True, host='192.168.10.11', port=10014, instrument_number=2)
        commander.exit()
        commander.switch_lamp_on() #address and port hardcoded
        commander.open_clarity_chrom("admin", config_file=r"C:\ClarityChrom\Cfg\automated_exp.cfg ", start_method=r"D:\Data2q\sugar-optimizer\autostartup_analysis\autostartup_005_Sugar-c18_shortened.MET")
        commander.slow_flowrate_ramp(r"D:\Data2q\sugar-optimizer\autostartup_analysis",
                                     method_list= ("autostartup_005_Sugar-c18_shortened.MET",
                                                   "autostartup_01_Sugar-c18_shortened.MET",
                                                   "autostartup_015_Sugar-c18_shortened.MET",
                                                   "autostartup_02_Sugar-c18_shortened.MET",
                                                   "autostartup_025_Sugar-c18_shortened.MET",
                                                   "autostartup_03_Sugar-c18_shortened.MET",
                                                   "autostartup_035_Sugar-c18_shortened.MET",
                                                   "autostartup_04_Sugar-c18_shortened.MET",
                                                   "autostartup_045_Sugar-c18_shortened.MET",
                                                   "autostartup_05_Sugar-c18_shortened.MET",))
        commander.load_file(r"D:\Data2q\sugar-optimizer\autostartup_analysis\auto_Sugar-c18_shortened.MET")
        #commander.load_file("opendedicatedproject") # open a project for measurements
        commander.set_sample_name("test123")
        commander.run()