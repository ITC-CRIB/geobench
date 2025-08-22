import os
import platform

from . import Executor


class ShellExecutor(Executor):
    """Shell executor class."""

    def get_config(self) -> dict:
        """Returns executor configuration."""
        system = platform.system()

        if system == 'Windows':
            shell = os.environ.get('COMSPEC')

        else:
            shell = os.environ.get('SHELL')

        config = {
            'executable': shell,
        }

        return config


    def get_arguments(self, command: str, args: dict) -> list:
        """Returns execution arguments for the specified command and arguments.

        Args:
            command (str): Command.
            args (dict): Arguments.

        Returns:
            List of execution arguments.
        """
        out = []

        system = platform.system()

        if system == 'Windows' and os.path.basename().lower() == 'cmd.exe':
            out.append('/C')

        out.append(command)

        for key, val in args:
            try:
                int(key)
                out.append(val)
            except:
                out.append(f"--{key}={val}")

        return out
