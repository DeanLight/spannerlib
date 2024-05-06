__version__ = "0.0.1"
from typing import Any
from .session import Session
from .spannerlog_magic import spannerlogMagic
from IPython import InteractiveShell, get_ipython

magic_session = Session()

def load_ipython_extension(ipython: InteractiveShell) -> None:
    # this method gets called when running `%load_ext spannerlog` or `import spannerlog` in jupyter
    ipython.register_magics(spannerlogMagic)

try:
    load_ipython_extension(get_ipython())
except (AttributeError, ImportError):
    pass
