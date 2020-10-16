import json

from IPython.core.magic import register_line_cell_magic
from rgxlog.rgxlog import Rgxlog
from IPython.core import magic_arguments

# noinspection PyTypeChecker
rgx: Rgxlog = None


@magic_arguments.magic_arguments()
@magic_arguments.argument('--shutdown', '-s',
                          action='store_const', const=True, dest='shutdown',
                          help='close the connection')
@magic_arguments.argument('--configure', '-c',
                          action='store_const', const=True, dest='configure',
                          help='send a json formatted configuration')
@register_line_cell_magic
def spanner(line, cell=None):
    global rgx
    args = magic_arguments.parse_argstring(spanner, line)

    if args.shutdown:
        if rgx:
            rgx.disconnect()
            rgx = None
            print('disconnected')
    else:
        if not rgx:
            user_config = dict()
            if args.configure:
                try:
                    user_config = json.loads(cell)
                except json.JSONDecodeError:
                    raise ValueError('cell is not in json format')

            rgx = Rgxlog(
                server_ip=user_config.get('remote_ip', None),
                port=user_config.get('remote_port', None),
                remote_run_command=user_config.get('remote_run_command', None),
                remote_kill_command=user_config.get('remote_kill_command', None),
                debug=user_config.get('debug', False)
            )
        else:
            result = rgx.execute(cell)
            print(result)
