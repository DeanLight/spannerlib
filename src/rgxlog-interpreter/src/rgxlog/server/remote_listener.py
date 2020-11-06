"""
Usage:
  remote_listener.py [--ip=<ip>] [--port=<port>]
  remote_listener.py (-h | --help)

Options:
  -h --help     Show this screen.
  --ip=<ip>     [default: localhost].
  --port=<port> [default: 32768].
"""
import logging
from docopt import docopt
from multiprocessing.queues import Queue
from multiprocessing.connection import Listener

from rgxlog.engine.pipeline import lark_pipeline
from rgxlog.system_configuration import system_configuration


def start_listener(ip, port=None, taken_port: Queue = None):
    """
    Starts a listener on the given ip and port (optional).
    When no port is supplied, the listener will try to bind to an available
    port and if it succeeds in doing so it will place the taken port in
    taken_port.
    """
    logging.basicConfig(format='%(asctime)s - %(message)s')

    # set a port range to iterate over when trying to bind
    if port is not None:
        min_port = port
        max_port = port
    else:
        min_port = system_configuration['default_local_client_config']['min_port']
        max_port = system_configuration['default_local_client_config']['max_port']
    port_range = range(min_port, max_port + 1)

    # look for an open port
    using_port = None
    for port in port_range:
        try:
            listener = Listener((ip, port))
        except OSError:
            logging.warning(f'port {port} is already taken')
        else:
            logging.info(f'listening on port {port}')
            using_port = port
            break

    if taken_port is not None:
        taken_port.put(using_port)  # notify the parent process which port was taken (None signifies failure)

    if using_port is None:
        logging.error(f'no suitable port in range [{min_port}, {max_port}] was found')
    else:
        # noinspection PyUnboundLocalVariable
        with listener.accept() as connection:
            logging.info(f'listener accepted connection from {listener.last_accepted}')

            while task := connection.recv():  # 'None' closes the connection
                result = lark_pipeline(task)
                connection.send(result)

        listener.close()
        logging.info('listener connection closed')


if __name__ == '__main__':
    args = docopt(__doc__)
    start_listener(ip=args['--ip'], port=int(args['--port']))
