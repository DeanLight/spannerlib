from typing import Any

import rgxlog.engine
import rgxlog.grammar
from rgxlog.engine.session import Session
from rgxlog.magic.rgxlog_magic import RgxlogMagic

magic_session = Session()


def load_ipython_extension(ipython: Any) -> None:
    # this method gets called when running `%load_ext rgxlog` or `import rgxlog` in jupyter
    ipython.register_magics(RgxlogMagic)


try:
    from IPython import get_ipython, InteractiveShell

    load_ipython_extension(get_ipython())

except (AttributeError, ImportError):
    pass
