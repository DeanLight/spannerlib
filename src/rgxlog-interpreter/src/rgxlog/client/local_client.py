import logging
from time import sleep
from multiprocessing.connection import Client

from rgxlog.server.connection_utils import get_connection_address
from rgxlog.system_configuration import system_configuration


def start_client(request_queue, reply_queue, remote_ip=None, remote_port=None):
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    if not remote_ip:
        address = get_connection_address('local_client')
        if remote_port:
            address[1] = remote_port
    else:
        address = (remote_ip, remote_port)

    connection_retries = system_configuration['default_local_client_config']['connection_retries']
    sleep_between_retries = system_configuration['default_local_client_config']['retry_sleep']

    for retry_number in range(connection_retries):
        try:
            with Client((address[0], address[1])) as conn:
                logging.info(f'client connected to {address[0]}:{address[1]}')
                while task := request_queue.get():
                    # print(f'client sending {task}')
                    conn.send(task)
                    reply = conn.recv()
                    # print(f'client received {reply}')
                    reply_queue.put(reply)
                conn.send(None)  # close the connection
                logging.info('client connection closed')
                break
        except EOFError:
            logging.info('client connection closed')
            break
        except (ConnectionRefusedError, OSError):
            logging.error(f'client connection to {address[0]}:{address[1]} refused')
            if retry_number < connection_retries - 1:
                logging.info(f'client retrying connection')
                sleep(sleep_between_retries)
    else:
        logging.error('client could not connect to listener, spanner cells will hang')
        # TODO: prevent spanners from waiting on the reply_queue in this case
