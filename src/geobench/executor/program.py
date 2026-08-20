"""Program executor module."""

import logging
import os
import platform
import subprocess
from abc import abstractmethod

import dotenv

from . import Executor, ExecutorOption

logger = logging.getLogger(__name__)


class ProgramExecutor(Executor):
    """Program executor class."""

    @classmethod
    def find_executable(cls, path: str, name: str) -> str | None:
        """Find executable with the specified path and name.

        Args:
            path: Path of the executable.
            name: Name of the executable.

        Returns:
            Path of the executable, or None if not found.
        """
        if not os.path.isdir(path):
            return None

        system = platform.system()

        for filename in os.listdir(path):
            if not filename.startswith(name):
                continue

            if system == "Windows":
                if filename.lower().endswith((".exe", ".bat", ".cmd")):
                    return os.path.join(path, filename)

            else:
                path = os.path.join(path, filename)
                if os.access(path, os.X_OK):
                    return path

        return None

    @classmethod
    def get_options(cls) -> dict[str, ExecutorOption]:
        """Return executor options."""
        return super().get_options() | {
            "executable": ExecutorOption(
                description="Executable name",
                type=str,
                required=True,
            ),
            "workdir": ExecutorOption(
                description="Set working directory",
                type=str,
            ),
            "env": ExecutorOption(
                description="Set environment variables (can be repeated)",
                type=dict,
            ),
            "env_file": ExecutorOption(
                description="Read in a file of environment variables.",
                type=str,
            ),
        }

    def __init__(self, config: dict | None = None, no_check: bool = False):
        """Initialize the program executor.

        Args:
            config: Optional configuration.

        Raises:
            ValueError: if no program executable is found.
        """
        super().__init__(config, no_check=no_check)
        self.process = None

    @abstractmethod
    def get_arguments(self, arguments: dict) -> list:
        """Return execution arguments for the specified arguments.

        Args:
            arguments: Arguments.

        Returns:
            List of execution arguments.
        """

    def get_cli_arguments(self, arguments: dict) -> list[str]:
        """Return arguments as command line arguments.

        Args:
            arguments: Arguments.

        Return:
            List of command line arguments.
        """
        out = []
        pos = {}

        for key, val in arguments.items():
            try:
                key = int(key)
            except ValueError:
                pass

            if isinstance(key, int):
                pos[key] = val
                continue

            if key[0] == "_":
                prefix = "-"
                key = key[1:]
            else:
                prefix = "--"

            try:
                key, subkey = key.split("__", 1)
                out.append(f"{prefix}{key}")
                out.append(f"{subkey}={val}")

            except ValueError:
                if val is True:
                    out.append(f"{prefix}{key}")
                else:
                    out.append(f"{prefix}{key}={val}")

        for key, val in sorted(pos.items()):
            out.append(val)

        return out

    def get_environment(self) -> dict:
        """Return environment considering the process environment."""
        env = os.environ.copy()

        if self.config.get("env_file"):
            env.update(dotenv.dotenv_values(self.config["env_file"]))

        env.update(self.config.get("env") or {})

        return env

    def execute(self, arguments: dict | None = None) -> int:
        """Execute program with the specified arguments.

        Args:
            arguments: Optional arguments.

        Returns:
            Process id of the program.
        """
        args = [self.config["executable"]] + self.get_arguments(arguments or {})
        logger.debug("Executing process with arguments: %s", args)

        self.process = subprocess.Popen(
            args,
            shell=False,
            cwd=self.config.get("workdir"),
            env=self.get_environment(),
        )

        return self.process.pid

    def wait(self):
        """Wait until execution ends.

        Raises:
            RuntimeError: If the program is not running.
        """
        if not self.process:
            raise RuntimeError("Program is not running")

        self.process.wait()
