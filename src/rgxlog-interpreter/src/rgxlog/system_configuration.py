# do not use this file to communicate between functions (except for initialization)

system_configuration = {
    'default_local_client_config': {
        # 'user_config_filename': 'local_client_user_config',
        # 'user_config_path': f'{os.path.dirname(os.path.abspath(rgxlog.__file__))}/server',
        'connection_retries': 3,
        'retry_sleep': 2,
        # 'ip': 'localhost',
        # 'port': 7945,
        'min_port': 2 ** 15,
        'max_port': 2 ** 16
    },

    'default_remote_listener_config': {
        # 'user_config_filename': 'remote_listener_user_config',
        # 'user_config_path': f'{os.path.dirname(os.path.abspath(rgxlog.__file__))}/server',
        # 'ip': '192.168.0.100',
        'ip': 'localhost',
        'port': 2 ** 15
    },
}
