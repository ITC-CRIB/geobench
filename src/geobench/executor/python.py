"""Python executor module."""

import os
import platform
import shutil

from . import ExecutorInfo
from .program import ProgramExecutor


class PythonExecutor(ProgramExecutor):
    """Python executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            type="python",
            name="Python Script Executor",
            description="Executes a Python script with arguments.",
        )

    def get_config(self, args: dict) -> dict:
        """Return executor configuration considering the arguments.

        Args:
            args: Configuration arguments.

        Raises:
            FileNotFoundError: If Python executable not found.
        """
        config = super().get_config(args)

        venv = args.get("venv")

        if venv:
            system = platform.system()

            if system == "Windows":
                names = ["Scripts/python.exe", "Scripts/python3.exe"]

            else:
                names = ["bin/python", "bin/python3"]

            found = False
            for name in names:
                path = os.path.join(venv, name)
                if os.path.isfile(path) or os.path.islink(path):
                    found = True
                    break

            if not found:
                raise FileNotFoundError(f"Python executable not found in: {venv}")

        else:
            path = shutil.which("python") or shutil.which("python3")
            if not path:
                raise FileNotFoundError("Python executable not found")

        config["executable"] = path

        return config

    def get_arguments(self, command: str, args: dict) -> list:
        """Return execution arguments for the specified command and arguments.

        Args:
            command: Command.
            args: Arguments.

        Returns:
            List of execution arguments.

        Raises:
            FileNotFoundError: If Python script not found.
        """
        if not os.path.isabs(command):
            command = os.path.join(self.config["workdir"], command)

        if not os.path.isfile(command):
            raise FileNotFoundError(f"Python script not found: {command}")

        out = [command] + self.get_cli_arguments(args)

        return out
