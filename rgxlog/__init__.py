__version__ = "0.0.1"
from typing import Any
from .session import Session
from .spanner_workbench_magic import spanner_workbenchMagic
from IPython import InteractiveShell, get_ipython

magic_session = Session()

def load_ipython_extension(ipython: InteractiveShell) -> None:
    # this method gets called when running `%load_ext spanner_workbench` or `import spanner_workbench` in jupyter
    ipython.register_magics(spanner_workbenchMagic)

try:
    load_ipython_extension(get_ipython())
except (AttributeError, ImportError):
    pass
