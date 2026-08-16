"""Python executor module."""

import os
import shutil
import subprocess
from pathlib import Path

from . import ExecutorInfo
from .program import ProgramExecutor


class PythonExecutor(ProgramExecutor):
    """Python executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            code="python",
            name="Python Script Executor",
            description="Executes a Python script with arguments.",
        )

    @classmethod
    def is_python_executable(cls, path: str) -> bool:
        try:
            subprocess.run(
                [path, "-c", "import sys; sys.exit(0)"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=True,
            )
            return True

        except (OSError, subprocess.SubprocessError):
            return False

    def prepare_config(self, config: dict) -> None:
        """Complete and validate the configuration options."""
        super().prepare_config(config)

        venv = config.get("venv")
        if venv:
            executable = os.path.join(venv, 
                "Scripts/python.exe" if os.name == "nt" else "bin/python"
            )
            if not (os.path.isfile(executable) or os.path.islink(executable)):
                raise FileNotFoundError(
                    f"Python executable not found in virtual environment: {venv}"
                )

            config["executable"] = executable

        if not config.get("executable"):
            executable = shutil.which("python") or shutil.which("python3")
            if executable is None:
                raise FileNotFoundError("Python executable not found")

            config["executable"] = executable

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
