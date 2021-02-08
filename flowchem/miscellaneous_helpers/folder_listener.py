from pathlib import Path
from threading import Thread
from queue import Queue
from time import sleep
import socket
import subprocess
import tenacity
from typing import Union

class FolderListener:
    # create the listener and create list of files present already
    def __init__(self, folder_path: str,  file_pattern: str):
        self.files = []
        self.new_files = Queue()
        for filepath in Path(folder_path).glob(file_pattern):
            if filepath not in self.files:
                self.files.append(filepath)
        self._watcher = Thread(target=self._watch_forever, args=(folder_path,file_pattern))
        self._watcher.start()

    def get_all_objects(self, folder_path: str,  file_pattern: str) -> iter:
        for filepath in Path(folder_path).glob(file_pattern):
            if filepath not in self.files:
                self.files.append(filepath)
                sleep(1)  # Let´s make sure that ClarityChrome has finished writing the file
                self.new_files.put(filepath)

    def _watch_forever(self, folder_path: str, file_pattern: str) -> None:
        while True:  # This could be replaced by some experiment_running flag
            self.get_all_objects(folder_path, file_pattern)
            sleep(1)


# some worker which takes from queue and sends file via socket is needed

class FileSender:
    """Sends new files from queue to a websocket"""
    def __init__(self, queue_object, host, port):
        self.host = host
        self.port = port
        self._sender = Thread(target=self.queue_worker(queue_object))
        self._sender.start()
        # call queue done when done and look for new
        pass

    def queue_worker(self, queue_name: Queue):
        while True:
            if not queue_name.empty():
                new_file_path = queue_name.get()
                self.open_socket_and_send(self.host, self.port, new_file_path)
                queue_name.task_done()
            sleep(1)

    @tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(2), reraise=True)
    def open_socket_and_send(self, host, port, path_to_file):
        s = socket.socket()
        s.connect((host, port))
        file_size = Path(path_to_file).stat().st_size

        s.send(f"{path_to_file.name}<SEPARATOR>{file_size}".encode())
        with open(path_to_file, 'rb') as f:
            while True:
                bytes_read = f.read(4096)
                if not bytes_read:
                    break
                s.sendall(bytes_read)
        s.close()



class FileReceiver:
    def __init__(self, server_host, server_port, directory_to_safe_to='D:\\transferred_chromatograms', buffer_size=4096, separator='<SEPARATOR>', allowed_address='192.168.1.12'):
        self.buffer_size = buffer_size
        self.allowed_address = allowed_address
        self.separator = separator
        self.s = socket.socket()
        self.s.bind((server_host, server_port))
        self.directory_to_safe_to = Path(directory_to_safe_to)
        self.s.listen(2)
        self.receiver = Thread(target=self.accept_new_connection)
        self.receiver.start()

    def accept_new_connection(self):
        while True:
            client_socket, address = self.s.accept()
            if not address[0] == self.allowed_address:
                client_socket.close()
                print(f'nice try {client_socket,address}')
            else:
                # if below code is executed, that means the sender is connected
                print(f"[+] {address} is connected.")
                self.receive_file(client_socket)
            sleep(1)

    def receive_file(self, client_socket):
        """
        receive the file infos
        receive using client socket, not server socket
        """
        received = client_socket.recv(self.buffer_size).decode()
        filename, file_size = received.split(self.separator)
        file_size = int(file_size)
        size_received = 0

        target_location = self.directory_to_safe_to / Path(filename)
        with target_location.open("wb") as f:
            while file_size > size_received:
                # read 1024 bytes from the socket (receive)
                bytes_read = client_socket.recv(self.buffer_size)
                if not bytes_read:
                    raise ConnectionAbortedError
                # TODO check
                size_received += len(bytes_read)
                f.write(bytes_read)
            # update the progress ba
        # close the client socket
        client_socket.close()


class MessageSender:
    def __init__(self, host, port):
        self.host = host
        self.port = port
    #encode('utf-8')

    @tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(2), reraise=True)
    def open_socket_and_send(self, message:str):
        s = socket.socket()
        s.connect((self.host, self.port))
        s.sendall(message.encode('utf-8'))
        s.close()

#
# sanitizing should be done
class ClarityExecutioner:
    """open up server socket. Everything coming in will be prepended with claritychrom.exe (if it is not already)"""
    command_prepend = 'claritychrom.exe'
    def __init__(self, port, allowed_client='192.168.10.20', host_ip='192.168.10.11'):
        self.port=port
        self.allowed_client=allowed_client
        self.host_ip=host_ip
        self.server_socket = self.open_server()
        self.executioner = Thread(target=self.get_commands_and_execute())
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
            print(f'nice try {client_socket,address}')
        else:
            # if below code is executed, that means the sender is connected
            print(f"[+] {address} is connected.")
            # in unicode
            request = client_socket.recv(1024).decode('utf-8')
            client_socket.close()
            print(request)
            return request


    def execute_command(self, command: str, folder_of_executable: Union[Path, str]=r'C:\claritychrom\bin\\'):
        prefix='claritychrom.exe'
        # sanitize input a bit
        if command.split(' ')[0] != prefix:
            command = folder_of_executable + prefix + ' ' + command
            print(command)
        x=subprocess.run(command, shell=True)
        return x

    def get_commands_and_execute(self):
        while True:
            self.execute_command(self.accept_new_connection())
            sleep(1)


if __name__ == "__main__":
    clarity_pc=True
    if clarity_pc:
        #start folder listener
        nosy = FolderListener(r"D:\exported_chromatograms", '*.txt')

        # start file transfer
        cleanly=FileSender(nosy.new_files, host='192.168.10.20', port=10339)

        # start command listener and executioner
        tattler = ClarityExecutioner(10237, allowed_client='192.168.10.20', host_ip='192.168.10.11')

    else:
        # start message sender (for clarity commands)
        messenger = MessageSender('192.168.10.11',  10237)
        archivist = FileReceiver('192.168.10.20', 10339, allowed_address='192.168.10.11')
