import logging
from itertools import cycle
from multiprocessing.connection import Listener
from multiprocessing.queues import Queue

from rgxlog.engine.pipeline import lark_pipeline
from rgxlog.server.connection_utils import get_connection_address
from rgxlog.system_configuration import system_configuration


def start_listener(good_port: Queue = None):
    address = get_connection_address('remote_listener')

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    if good_port:
        max_port = system_configuration['default_local_client_config']['max_port']
    else:
        max_port = address[1] + 1

    try:
        for port in cycle(range(address[1], max_port + 1)):
            address[1] = port
            try:
                with Listener((address[0], address[1])) as listener:
                    logging.info(f'listening on {address[0]}:{address[1]}')
                    if good_port:
                        # notify the parent process what port was successfully taken (to later tell the client about it)
                        good_port.put(address[1])
                    with listener.accept() as conn:
                        logging.info(f'listener accepted connection from {listener.last_accepted}')
                        while msg := conn.recv():  # 'None'/EOF closes the connection
                            result = lark_pipeline(msg)  # showtime
                            conn.send(result)
                        logging.info('server got finish signal')
                        break
            except OSError:  # port already taken
                logging.info(f'port {port} taken, trying a different one...')
        logging.info('listener connection closed')
    except EOFError:
        logging.info('listener connection closed')


if __name__ == '__main__':
    start_listener()
