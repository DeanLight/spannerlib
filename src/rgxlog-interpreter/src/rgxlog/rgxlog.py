import shlex
import subprocess
from multiprocessing import Queue
from multiprocessing.context import Process
from rgxlog.client.local_client import start_client
from rgxlog.server.remote_listener import start_listener


class Rgxlog:
    def __init__(self, ip=None, port=None, remote_run_command=None, remote_kill_command=None, debug=False):
        self._remote = False
        if bool(remote_run_command) != bool(remote_kill_command):
            raise ValueError('remote_run_command and remote_kill_command must be set together')
        elif remote_run_command:  # if both are set, we are running the server remotely
            self._remote = True

        self._debug = debug
        self._remote_run_command = remote_run_command
        self._remote_kill_command = remote_kill_command
        self._remote_ip = ip
        self._remote_port = port
        self._reply_queue = Queue()
        self._request_queue = Queue()
        self._good_port = Queue(1)

        if self._debug:
            self._debug_server_init()
        elif self._remote:
            self._remote_server_init()
        else:  # server runs locally
            self._local_server_init()

        client_args = (self._request_queue, self._reply_queue, self._remote_ip, self._remote_port)
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
        elif self._remote:
            self._remote_server_disconnect()
        else:
            self._local_server_disconnect()

    @staticmethod
    def _debug_server_init():
        print("don't forget to manually run the server!")

    def _remote_server_init(self):
        # listener_process.start() remotely
        assert self._remote_run_command
        subprocess.Popen(shlex.split(self._remote_run_command))

    def _local_server_init(self):
        self.listener_process = Process(target=start_listener, args=(self._good_port,))
        self.listener_process.start()
        self._remote_port = self._good_port.get()

    @staticmethod
    def _debug_server_disconnect():
        print("don't forget to manually stop the server!")

    def _remote_server_disconnect(self):
        assert self._remote_kill_command
        command = self._remote_kill_command
        subprocess.Popen(shlex.split(command))

    def _local_server_disconnect(self):
        self.listener_process.join()
