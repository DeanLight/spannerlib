import json
from rgxlog.system_configuration import system_configuration


def get_connection_address(configuration):
    assert configuration in ('local_client', 'remote_listener')

    default = system_configuration[f'default_{configuration}_config']
    address_ = (default['ip'], default['port'])
    user_config_file_name = default['user_config_filename']
    user_config_file_path = default['user_config_path']

    try:
        with open(f'{user_config_file_path}/{user_config_file_name}', 'r') as config:
            config = json.loads(config.read())
            address_ = (config['ip'], config['port'])
    except FileNotFoundError:
        # print(f'{user_config_file_name} in directory {user_config_file_path} not found')
        # print(f'loading defaults')
        pass
    except json.JSONDecodeError:
        print(f'{user_config_file_name} is in the wrong format')
        exit()
    except KeyError as e:
        print(f'{user_config_file_name} is missing the key {e}')
        exit()

    return address_
