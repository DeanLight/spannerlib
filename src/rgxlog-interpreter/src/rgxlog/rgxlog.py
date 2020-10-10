import shlex
import subprocess
from multiprocessing import Queue
from multiprocessing.context import Process
from rgxlog.client.local_client import start_client
from rgxlog.server.remote_listener import start_listener


class Rgxlog:
    def __init__(self, server_ip=None, port=None, remote_run_command=None, remote_kill_command=None, debug=False):
        if server_ip and server_ip not in ('localhost', '127.0.0.1') \
                and not all((port, remote_run_command, remote_kill_command)):
            raise ValueError('missing port / run command / kill command')

        self._running_remotely = server_ip and server_ip not in ('localhost', '127.0.0.1')
        self._debug = debug
        self._remote_run_command = remote_run_command
        self._remote_kill_command = remote_kill_command
        self._remote_ip = server_ip
        self._remote_port = port
        self._reply_queue = Queue(1)
        self._request_queue = Queue(1)
        self._port_pipe = Queue(1)

        if self._debug:
            self._debug_server_init()
        elif self._running_remotely:
            self._remote_server_init()
        else:
            self._local_server_init()

        client_args = (self._request_queue, self._reply_queue, self._remote_port, self._remote_ip)
        self._client_process = Process(target=start_client, args=client_args)
        self._client_process.start()

    def execute(self, query):
        if not query:
            raise ValueError('empty query!')

        self._request_queue.put(query)
        reply = self._reply_queue.get()
        return reply

    def disconnect(self):
        # 'None' message notifies the client to finish
        self._request_queue.put(None)  # TODO: make a standard message format
        self._client_process.join()

        if self._debug:
            self._debug_server_disconnect()
        elif self._running_remotely:
            self._remote_server_disconnect()
        else:
            self._local_server_disconnect()

    @staticmethod
    def _debug_server_init():
        print("don't forget to manually run the server!")

    def _remote_server_init(self):
        assert self._remote_run_command
        subprocess.Popen(shlex.split(self._remote_run_command))

    def _local_server_init(self):
        if self._remote_port:
            listener_args = ('localhost', self._remote_port, None)
            self.listener_process = Process(target=start_listener, args=listener_args)
            self.listener_process.start()
        else:
            listener_args = ('localhost', None, self._port_pipe)
            self.listener_process = Process(target=start_listener, args=listener_args)
            self.listener_process.start()
            self._remote_port = self._port_pipe.get()

    @staticmethod
    def _debug_server_disconnect():
        print("don't forget to manually stop the server!")

    def _remote_server_disconnect(self):
        assert self._remote_kill_command
        command = self._remote_kill_command
        subprocess.Popen(shlex.split(command))

    def _local_server_disconnect(self):
        self.listener_process.join()
