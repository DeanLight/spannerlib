import shlex
from subprocess import Popen, PIPE
from threading import Timer
from typing import Iterable

import psutil
from sys import platform

WINDOWS_OS = "win32"
IS_POSIX = (platform != WINDOWS_OS)


def kill_process_and_children(process: Popen):
    print("~~~~ process timed out ~~~~")
    if process.poll() is not None:
        ps_process = psutil.Process(process.pid)
        for child in ps_process.children(recursive=True):  # first, kill the children :)
            child.kill()  # not recommended in real life
        process.kill()  # lastly, kill the process


def run_command(command: str, stdout=True, stderr=False, shell=False, timeout=-1) -> Iterable[str]:
    """
    this utility can be used to run any cli command, and iterate over the output
    :param timeout: if positive, kill the process after `timeout` seconds. default: `-1`
    :param stdout: if true, yield output from stdout. default: `True`
    :param stderr: if true, suppress stderr output. default: `False`
    :param shell: if true, spawn shell process (e.g. /bin/sh), which allows using system variables (e.g. $HOME),
        but is considered a security risk (see:
        https://docs.python.org/3/library/subprocess.html#security-considerations)
    :param command: a single command string
    :return: string iterator
    """
    # `shlex.split` just splits the command into a list properly
    command_list = shlex.split(command, posix=IS_POSIX)
    stdout = PIPE if stdout else None
    stderr = PIPE if stderr else None

    process = Popen(command_list, stdout=stdout, stderr=stderr, shell=shell)

    # set timer
    my_timer = None
    if timeout > 0:
        # set timer to kill the process
        my_timer = Timer(timeout, kill_process_and_children, [process])
        my_timer.start()

    # get output
    while True:
        output = process.stdout.readline()  # type(output) == bytes
        output = output.decode("utf-8").strip()  # convert to `str` and remove the `\n` at the end of every line
        if output:
            yield output
        elif process.poll() is not None:  # process died
            if my_timer is not None:
                my_timer.cancel()
            return
