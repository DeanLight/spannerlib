import argparse
import logging
from itertools import cycle
from multiprocessing.connection import Listener
from multiprocessing.queues import Queue

from rgxlog.engine.pipeline import lark_pipeline
from rgxlog.system_configuration import system_configuration


def start_listener(ip, port=None, port_pipe: Queue = None):
    assert (port and not port_pipe) or (port_pipe and not port)
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    if port_pipe:
        min_port = system_configuration['default_local_client_config']['min_port']
        max_port = system_configuration['default_local_client_config']['max_port']
        port_range = cycle(range(min_port, max_port + 1))
    else:  # port was set manually
        port_range = (port,)

    for port in port_range:
        try:
            with Listener((ip, port)) as listener:
                logging.info(f'listening on {ip}:{port}')

                if port_pipe:
                    port_pipe.put(port)  # notify the parent process what port was successfully taken

                with listener.accept() as conn:
                    logging.info(f'listener accepted connection from {listener.last_accepted}')

                    while msg := conn.recv():  # 'None' closes the connection
                        result = lark_pipeline(msg)  # showtime
                        conn.send(result)

                    break
        except OSError:  # port already taken
            logging.info(f'port {port} taken, trying a different one...')
    logging.info('listener connection closed')


if __name__ == '__main__':
    default_ip = system_configuration['default_remote_listener_config']['ip']
    default_port = system_configuration['default_remote_listener_config']['port']

    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', type=str, default=default_ip)
    parser.add_argument('--port', type=int, default=default_port)
    args = parser.parse_args()

    start_listener(args.ip, args.port)
