try:
    import rgxlog.magic.rgxlog_magic
except NameError:
    # when the remote server imports system_configuration.py it has to run this
    # file when this happens, rgxlog_magic throws this error because it has to
    # be ran from a jupyter notebook and a remote server runs standalone
    pass

import rgxlog.engine
from rgxlog.rgxlog import Rgxlog
