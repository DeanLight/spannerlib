import logging
import shlex
import subprocess
from multiprocessing import Queue
from multiprocessing.connection import Client as Client_
from multiprocessing.context import Process
from time import sleep

from rgxlog.server.remote_listener import start_listener
from rgxlog.system_configuration import system_configuration


class Client:
    """
    Instances of this class serve as clients that connect to an rgxlog server
    and send queries for evaluation
    """

    def __init__(self,
                 remote_ip='localhost',
                 remote_port=None,
                 remote_run_command=None,
                 remote_kill_command=None,
                 remote_debug=False):
        """
        :param remote_ip: Server ip
        :param remote_port: Server port
        :param remote_run_command: [DEBUG] shell command to start the remote server
        :param remote_kill_command: [DEBUG] shell command to kill the remote server in case it hangs unexpectedly
        :param remote_debug: [DEBUG] enable remote_{run, kill}_command for remote debugging
        """
        self._running_remotely = remote_ip and remote_ip not in ('localhost', '127.0.0.1')

        if not remote_debug and any((remote_run_command, remote_kill_command)):
            raise ValueError('remote run / kill commands are only valid when debugging')
        if remote_debug and not all((remote_port, remote_run_command, remote_kill_command)):
            raise ValueError('missing port / run command / kill command')
        if self._running_remotely and not all((remote_ip, remote_port)):
            raise ValueError('missing remote_ip / remote_port')

        self._remote_ip = remote_ip
        self._remote_port = remote_port
        self._remote_run_command = remote_run_command
        self._remote_kill_command = remote_kill_command
        self._remote_debug = remote_debug

        self._taken_port = Queue(1)
        self._connection = None

        self.connected = False

        if self._running_remotely:
            if self._remote_debug:
                self._start_remote_debug_server()
        else:
            self._run_local_server()

        self.connect()

    def __del__(self):
        self.disconnect()

    def connect(self):
        """
        Establish a connection to the server
        """
        if self.connected:
            return

        logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

        connection_retries = system_configuration['default_local_client_config']['connection_retries']
        sleep_between_retries = system_configuration['default_local_client_config']['retry_sleep']

        last_retry = connection_retries - 1
        for retry_number in range(connection_retries):
            try:
                self._connection = Client_((self._remote_ip, self._remote_port))
                break
            except (ConnectionRefusedError, OSError):
                logging.warning(f'client connection to {self._remote_ip}:{self._remote_port} refused')
                if retry_number != last_retry:
                    sleep(sleep_between_retries)
                    logging.info(f'client retrying connection')

        if self._connection is None:
            logging.error('client could not connect to listener')
        else:
            logging.info(f'client connected to {self._remote_ip}:{self._remote_port}')
            self.connected = True

    def disconnect(self):
        """
        Disconnect from the server
        """
        if self.connected:
            self._connection.send(None)  # 'None' message notifies the client to finish
            self._connection.close()
            logging.info('client connection closed')

            if self._running_remotely:
                if self._remote_debug:
                    self._stop_remote_debug_server()
            else:
                self._stop_local_server()
            self.connected = False

    def execute(self, query):
        """
        Send the query for execution
        :return: Query result
        """
        if not self.connected:
            raise ConnectionError
        if not query:
            raise ValueError('empty query!')

        try:
            self._connection.send(query)
            reply = self._connection.recv()
        except EOFError:
            logging.error('client connection closed unexpectedly')
            reply = None

        return reply

    def _run_local_server(self):
        """
        Starts the server locally
        """
        if self._remote_port:
            listener_args = ('localhost', self._remote_port, self._taken_port)
        else:
            listener_args = ('localhost', None, self._taken_port)

        self._listener_process = Process(target=start_listener, args=listener_args)
        self._listener_process.start()
        self._remote_port = self._taken_port.get()

        if self._remote_port is None:
            raise ConnectionError

    def _stop_local_server(self):
        """
        Stops the local server
        """
        self._listener_process.join()

    def _start_remote_debug_server(self):
        """
        [DEBUG]
        Uses the remote run command to start the remote server for debugging
        """
        assert self._remote_run_command
        subprocess.Popen(shlex.split(self._remote_run_command))
        # TODO: some handshake

    def _stop_remote_debug_server(self):
        """
        [DEBUG]
        Uses the remote kill command to kill the remote server if it hangs unexpectedly
        """
        assert self._remote_kill_command
        command = self._remote_kill_command
        subprocess.Popen(shlex.split(command))


if __name__ == '__main__':
    from rgxlog import magic_client

    result = magic_client.execute('parent("bob")')
    magic_client.disconnect()
    print(result)
