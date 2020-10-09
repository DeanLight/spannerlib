import json

# from IPython import get_ipython
from IPython.core.magic import register_cell_magic
from rgxlog.rgxlog import Rgxlog

# from IPython.core.magic import (Magics, magics_class, cell_magic)

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
        ip=user_config.get('remote_ip', None),
        port=user_config.get('remote_port', None),
        remote_run_command=user_config.get('remote_run_command', None),
        remote_kill_command=user_config.get('remote_kill_command', None),
        debug=user_config.get('debug', False)
    )


# noinspection PyUnusedLocal
@register_cell_magic
def spanner(line, cell):
    global rgx

    if not rgx:
        rgx = Rgxlog()

    result = rgx.execute(cell)
    print(result)


# noinspection PyUnusedLocal
@register_cell_magic
def finalize(line, cell):
    global rgx

    if rgx:
        rgx.disconnect()
        rgx = None

# @magics_class
# class SpannerMagics(Magics):
#     def __init__(self, shell):
#         super(SpannerMagics, self).__init__(shell)
#
#     @cell_magic
#     def test(self, line, cell):
#         # print(self.shell.user_ns)
#         print(self.shell.user_ns['z'])
#
#
# ip = get_ipython()
# ip.register_magics(SpannerMagics)
