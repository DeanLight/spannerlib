from rgxlog.engine.session import Session
import rgxlog.engine
import rgxlog.grammar
from rgxlog.magic.rgxlog_magic import RgxlogMagic

magic_session = Session()


def load_ipython_extension(ipython):
    ipython.register_magics(RgxlogMagic)
