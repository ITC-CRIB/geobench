"""Python executor module."""

import os
import platform
import shutil

from . import Executor, ExecutorInfo


class PythonExecutor(Executor):
    """Python executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            type="python",
            name="Python Script Executor",
            description="Executes a Python script with arguments.",
        )

    def get_config(self) -> dict:
        """Return executor configuration.

        Raises:
            FileNotFoundError: If Python executable not found.
        """
        config = {}

        venv = self.scenario.venv

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
            command = os.path.join(self.scenario.workdir, command)

        if not os.path.isfile(command):
            raise FileNotFoundError(f"Python script not found: {command}")

        out = [command]

        for key, val in args.items():
            try:
                int(key)
                out.append(val)
            except Exception:
                out.append(f"--{key}={val}")

        return out
