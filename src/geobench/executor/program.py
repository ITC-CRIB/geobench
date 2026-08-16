"""Program executor module."""

import logging
import os
import platform
import subprocess
from abc import abstractmethod

import dotenv

from ..utils import KeyValueAction
from . import Executor, ExecutorOption

logger = logging.getLogger(__name__)


class ProgramExecutor(Executor):
    """Program executor class."""

    @staticmethod
    def find_executable(path: str, name: str) -> str | None:
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
    def get_options(self) -> dict[str, ExecutorOption]:
        """Return executor options."""
        return {
            "executable": ExecutorOption(
                description="Name of the executable",
                type=str,
                required=True,
                positional=True,
            ),
            "workdir": ExecutorOption(
                description="Working directory",
                type=str,
            ),
            "env": ExecutorOption(
                description="Set environmet variables",
                type=dict,
                action=KeyValueAction,
            ),
            "env-file": ExecutorOption(
                description="Read in a file of environment variables.",
                type=str,
            ),
        }

    def __init__(self, config: dict | None = None):
        """Initialize the program executor.

        Args:
            config: Optional configuration.

        Raises:
            ValueError: if no program executable is found.
        """
        super().__init__(config)
        self.process = None

    def prepare_config(self, config: dict) -> dict:
        """Return executor configuration considering the arguments.

        Args:
            args: Configuration arguments.
        """
        if config.get("env-file"):
            env = dotenv.dotenv_values(config["env-file"])
        else:
            env = {}

        env.update(config.get("env", {}))

        config["environment"] = env

    @abstractmethod
    def get_arguments(self, command: str, args: dict) -> list:
        """Return execution arguments for the specified command and arguments.

        Args:
            command: Command.
            args: Arguments.

        Returns:
            List of execution arguments.
        """

    def get_cli_arguments(self, args: dict) -> list[str]:
        """Return arguments as command line arguments.

        Args:
            args: Arguments.

        Return:
            List of command line arguments.
        """
        out = []
        pos = {}

        for key, val in args.items():
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
        env.update(self.config.get("environment", {}))
        return env

    def execute(self, command: str, args: dict | None = None) -> int:
        """Execute program command with the specified arguments.

        Args:
            command: Program command.
            args: Optional arguments.

        Returns:
            Process id of the program.
        """
        args = [self.config["executable"]] + self.get_arguments(command, args or {})
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
