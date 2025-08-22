import os
import platform
import shutil

from . import Executor


class PythonExecutor(Executor):
    """Python executor class."""

    def get_config(self) -> dict:
        """Returns executor configuration."""
        config = {}

        venv = self.scenario.venv

        if venv:
            system = platform.system()

            if system == 'Windows':
                names = ['Scripts/python.exe', 'Scripts/python3.exe']

            else:
                names = ['bin/python', 'bin/python3']

            found = False
            for name in names:
                path = os.path.join(venv, name)
                if os.path.isfile(path) or os.path.islink(path):
                    found = True
                    break

            if not found:
                raise FileNotFoundError("Python executable not found in {}.".format(venv))

        else:
            path = shutil.which('python') or shutil.which('python3')
            if not path:
                raise FileNotFoundError("Python executable not found.")

        config['executable'] = path

        return config


    def get_arguments(self, command: str, args: dict) -> list:
        """Returns execution arguments for the specified command and arguments.

        Args:
            command (str): Command.
            args (dict): Arguments.
        
        Returns:
            List of execution arguments.
        """
        if not os.path.isabs(command):
            command = os.path.join(self.scenario.workdir, command)

        if not os.path.isfile(command):
            raise FileNotFoundError("Python script not found.")

        out = [command]

        for key, val in args:
            try:
                int(key)
                out.append(val)
            except:
                out.append(f"--{key}={val}")

        return out
