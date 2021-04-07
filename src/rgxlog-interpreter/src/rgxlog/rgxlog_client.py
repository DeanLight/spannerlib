# TODO: delete this file
import csv
import logging
import shlex
import subprocess
from multiprocessing import Queue
from multiprocessing.connection import Client as Client_
from multiprocessing.context import Process
from time import sleep

from pandas import DataFrame
from rgxlog.engine.message_definitions import Request
from rgxlog.system_configuration import system_configuration
from rgxlog.engine.session import Session


class Client:

    # TODO: delete unnecessary members.
    def __init__(self,
                 session=Session(),
                 remote_ip='localhost',
                 remote_port=None,
                 remote_run_command=None,
                 remote_kill_command=None,
                 remote_debug=False):
        """
        Args:
            remote_ip: server ip
            remote_port: port
            remote_run_command: [DEBUG] shell command to start the remote server
            remote_kill_command: [DEBUG] shell command to kill the remote server in case it hangs unexpectedly
            remote_debug: [DEBUG] enable remote_{run, kill}_command for remote debugging
        """
        self._running_remotely = remote_ip not in ('localhost', '127.0.0.1')

        if not remote_debug and (remote_run_command or remote_kill_command):
            raise ValueError('remote run / kill commands are only valid when debugging')
        if remote_debug and not (remote_port and remote_run_command and remote_kill_command):
            raise ValueError('missing port / run command / kill command')
        if self._running_remotely and not (remote_ip and remote_port):
            raise ValueError('missing remote_ip / remote_port')

        self._remote_ip = remote_ip
        self._remote_port = remote_port
        self._remote_run_command = remote_run_command
        self._remote_kill_command = remote_kill_command
        self._remote_debug = remote_debug

        self._taken_port = Queue(1)  # used to notify the parent process which port was taken by the server
        self._connection = None

        self.connected = False

        if self._running_remotely and self._remote_debug:
            self._start_remote_debug_server()
        elif not self._running_remotely:
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
            logging.error('client could not connect to server')
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

        query_message = {
            'msg_type': Request.QUERY,
            'data': query
        }

        try:
            self._connection.send(query_message)
            reply = self._connection.recv()
        except EOFError:
            logging.error('client connection closed unexpectedly')
            reply = {'data': None}

        return reply['data']

    def register(self, ie_function, ie_function_name, in_rel, out_rel, is_super_user=False):
        """
        Register the ie name for future usage
        :return: True for successful registration, false otherwise
        """
        self.session.register_ie_function(ie_function, ie_function_name, in_rel, out_rel, is_super_user)
        # TODO: return value

    def import_relation_from_csv(self, csv_file_name, relation_name):
        # TODO: this is pseudo-code only

        """
        reader = open csv file
        relation_name = get name of relation

        for line in reader:
            parse the line (relation name, types) into AddFact object
            add to list

        # create relation if it does not exist
        symbol_table = session._symbol_table
        engine = session._execution (why don't we rename this?)

        if not symbol_table.contains_relation(relation_name):
            engine.declare_relation(relation_name)

        # add list to relation
        for item in list:
            engine.add_fact(item)

        """
        raise NotImplementedError

    def import_relation_from_df(self, df: DataFrame, relation_name):
        # TODO: this is pseudo-code only
        """
        same as import from csv but use df.to_numpy().tolist()
        """
        raise NotImplementedError

    def export_relation_to_csv(self, csv_file_name, relation_name):
        # TODO
        """
        this will be implemented in a future version
        """
        raise NotImplementedError

    def export_relation_to_df(self, df, relation_name):
        # TODO
        """
        this will be implemented in a future version
        """
        raise NotImplementedError

    def query_into_csv(self, query, csv_file_name):
        # TODO: this is pseudo-code only
        #  we should have access to the session after deleting the server file
        #  (execution is imported from the engine)
        """
        # run a query normally and get formatted results:
        free_vars, rows = execution.get_query_results(self._session.query(query))
        if not rows:
            rows = [free_vars]
        else:
            # add free_vars at start of csv
            rows.insert(0, free_vars)

        with open(csv_file_name,w) as f:
          writer = csv.writer(f)
          writer.writerows(rows)
        """
        raise NotImplementedError

    def query_into_df(self, query) -> DataFrame:
        # TODO: this is pseudo-code only
        """
        should be similar to query_into_csv:
        free_vars, rows = execution.get_query_results(self._session.query(query))
        df = DataFrame(rows, columns=free_vars)
        """
        raise NotImplementedError

    def get_pass_stack(self):
        """
        Fetches the current pass stack
        :return: a list of passes
        """
        if not self.connected:
            raise ConnectionError

        request_stack_message = {
            'message_type': Request.CURRENT_STACK,
        }

        try:
            self._connection.send(request_stack_message)
            reply = self._connection.recv()
        except EOFError:
            logging.error('client connection closed unexpectedly')
            reply = {'data': None}

        return reply['data']

    def set_pass_stack(self, user_stack):
        """
        Sets the current pass stack
        """
        if not self.connected:
            raise ConnectionError
        if type(user_stack) is not list:
            raise ValueError('user stack should be a list of pass names (strings)')
        for pass_ in user_stack:
            if type(pass_) is not str:
                raise ValueError('user stack should be a list of pass names (strings)')

        request_set_stack_message = {
            'message_type': Request.SET_STACK,
            'data': user_stack
        }

        try:
            self._connection.send(request_set_stack_message)
            reply = self._connection.recv()
        except EOFError:
            logging.error('client connection closed unexpectedly')
            reply = {'data': None}

        return reply['data']

    def _run_local_server(self):
        """
        Starts the server locally
        """
        if self._remote_port:
            server_args = ('localhost', self._remote_port, self._taken_port)
        else:
            server_args = ('localhost', None, self._taken_port)

        self._server_process = Process(target=start_server, args=server_args)
        self._server_process.start()
        self._remote_port = self._taken_port.get()

        if self._remote_port is None:
            raise ConnectionError

    def _stop_local_server(self):
        """
        Stops the local server
        """
        self._server_process.join()

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


# TODO: this main is used for debugging only - not for production
if __name__ == '__main__':
    client = Client()
    result = client.execute('''
        new uncle(str, str)
        uncle("bob", "greg")
        ''')
    print("result1:")
    print(result)
    result = client.execute('''?uncle("bob",Y)''')
    print("result2:")
    print(result)
