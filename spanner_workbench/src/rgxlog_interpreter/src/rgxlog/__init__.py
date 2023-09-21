from typing import Any

from .engine.session import Session
from .magic.rgxlog_magic import RgxlogMagic
from IPython import InteractiveShell, get_ipython

magic_session = Session()


def load_ipython_extension(ipython: InteractiveShell) -> None:
    # this method gets called when running `%load_ext rgxlog` or `import rgxlog` in jupyter
    ipython.register_magics(RgxlogMagic)


try:
    load_ipython_extension(get_ipython())

except (AttributeError, ImportError):
    pass
