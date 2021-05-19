from rgxlog.engine.session import Session
import rgxlog.engine
import rgxlog.grammar
from rgxlog.magic.rgxlog_magic import RgxlogMagic

magic_session = Session()


def load_ipython_extension(ipython):
    # TODO@niv: @dean, we can put this in a global scope inside a try-except if needed
    #  however, according to https://ipython.readthedocs.io/en/stable/config/custommagics.html, looks like this is
    #  the common way to load the magic
    # @response: if this is the recommended way and it works, go for it
    ipython.register_magics(RgxlogMagic)
