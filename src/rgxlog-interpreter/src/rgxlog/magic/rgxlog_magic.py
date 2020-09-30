import json
import shlex
import subprocess

from multiprocessing import Process, Queue
from IPython.core.magic import register_cell_magic
from rgxlog.server.local_client import start_client
from rgxlog.server.remote_listener import start_listener

configuration = dict()
reply_queue = Queue()
request_queue = Queue()
client_process: Process
listener_process: Process
initialized = False


# TODO: clean spaghetti
# TODO: load state? (make state per-notebook?)
# TODO: make a standard config format and check adherence to it
# TODO: configuration['run'] = debug/local/remote
# TODO: sane defaults for when configuration is empty / partially empty
@register_cell_magic
def initialize(line, cell):
    global request_queue
    global reply_queue
    global client_process
    global listener_process
    global configuration
    global initialized

    try:
        configuration = json.loads(cell)
    except json.JSONDecodeError:
        print('cell is not in json format')
        exit()

    command = configuration.get('remote_run_command', None)
    remote_ip = configuration.get('remote_ip', None)
    remote_port = configuration.get('remote_port', None)

    if configuration.get('run', 'local') == 'local':
        listener_process = Process(target=start_listener)
        listener_process.start()
    elif configuration['run'] == 'remote':
        subprocess.Popen(shlex.split(command))  # listener_process.start() remotely
    else:
        # debug, (so we start the server manually in an IDE)
        pass

    client_process = Process(target=start_client, args=(request_queue, reply_queue, remote_ip, remote_port))
    client_process.start()

    initialized = True


@register_cell_magic
def spanner(line, cell):
    global initialized
    global request_queue
    global reply_queue

    if not initialized:
        initialize(None, '{}')

    # send cell to client
    request_queue.put(cell)
    # wait for server response
    reply = reply_queue.get()
    # notebook prints the result
    print(reply)


# TODO: save state?
@register_cell_magic
def finalize(line, cell):
    global request_queue
    global listener_process
    global configuration
    global initialized

    request_queue.put(None)  # stops client, and the client does the same to listener
    client_process.join()

    # only used if listener was started and no connection was made (the listener is deadlocked waiting to connect)
    if 'remote_kill_command' in configuration and configuration['run'] == 'remote':
        command = configuration['remote_kill_command']
        subprocess.Popen(shlex.split(command))
    else:
        listener_process.join()

    initialized = False
