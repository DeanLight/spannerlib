try:
    import rgxlog.magic.rgxlog_magic
except NameError:
    # when the remote server imports system_configuration.py it has to run this
    # file. when this happens, rgxlog_magic throws this exception because magics
    # have to be ran from a jupyter notebook and a remote server runs outside of jupyter
    pass
else:
    import rgxlog.engine
    from rgxlog.rgxlog_client import Client

    magic_client = Client()
