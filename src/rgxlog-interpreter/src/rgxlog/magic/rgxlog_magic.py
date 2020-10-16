import json

from IPython.core.magic import register_cell_magic, register_line_magic, register_line_cell_magic
from rgxlog.rgxlog import Rgxlog
from IPython.core import magic_arguments

# noinspection PyTypeChecker
rgx: Rgxlog = None


# noinspection PyUnusedLocal
@register_cell_magic
def initialize(line, cell):
    global rgx

    user_config = dict()
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


@magic_arguments.magic_arguments()
@magic_arguments.argument('--shutdown', '-s', action='store_const', const=True, dest='shutdown', help='testing')
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
            rgx = Rgxlog()

        result = rgx.execute(cell)
        print(result)
