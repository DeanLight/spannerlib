import logging
from time import sleep
from multiprocessing.connection import Client

from rgxlog.system_configuration import system_configuration


def start_client(request_queue, reply_queue, remote_port, remote_ip='localhost'):
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    ip = 'localhost' if not remote_ip else remote_ip
    port = remote_port

    connection_retries = system_configuration['default_local_client_config']['connection_retries']
    sleep_between_retries = system_configuration['default_local_client_config']['retry_sleep']

    for retry_number in range(connection_retries):
        try:
            with Client((ip, port)) as conn:
                logging.info(f'client connected to {ip}:{port}')

                while task := request_queue.get():
                    conn.send(task)
                    reply = conn.recv()
                    reply_queue.put(reply)

                conn.send(None)  # notify server to shutdown
                logging.info('client connection closed')
                break
        except EOFError:
            logging.info('client connection closed')
            break
        except (ConnectionRefusedError, OSError):
            logging.error(f'client connection to {ip}:{port} refused')
            if retry_number < connection_retries - 1:
                logging.info(f'client retrying connection')
                sleep(sleep_between_retries)
    else:
        logging.error('client could not connect to listener, spanner cells will hang')
        # TODO: prevent spanners from waiting on the reply_queue in this case
