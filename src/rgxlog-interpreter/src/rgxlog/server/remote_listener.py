import logging
from multiprocessing.connection import Listener

from rgxlog.engine.pipeline import lark_pipeline
from rgxlog.server.connection_utils import get_connection_address


def start_listener():
    address = get_connection_address('remote_listener')

    # logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    try:
        with Listener(address) as listener:
            logging.info(f'listening on {address[0]}:{address[1]}')
            with listener.accept() as conn:  # if no connection is made it gets stuck here and requires an external kill
                logging.info(f'listener accepted connection from {listener.last_accepted}')
                while msg := conn.recv():  # 'None'/EOF closes the connection
                    result = lark_pipeline(msg)  # showtime
                    conn.send(result)
        logging.info('listener connection closed')
    except EOFError:
        logging.info('listener connection closed')


if __name__ == '__main__':
    start_listener()
