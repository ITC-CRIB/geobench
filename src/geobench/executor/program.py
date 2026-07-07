"""Program executor module."""

from abc import abstractmethod
import os
import platform
import subprocess

import psutil

from . import Executor


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

    def __init__(self, config: dict | None = None):
        """Initialize the program executor.

        Args:
            config: Optional configuration.

        Raises:
            ValueError: if no program executable is found.
        """
        super().__init__(config)

        if not self.config["executable"]:
            raise ValueError("No program executable found")

    def get_config(self, args: dict) -> dict:
        """Return executor configuration considering the arguments.

        Args:
            args: Configuration arguments.
        """
        config = {
            "workdir": args.get("workdir"),
            "environment": {},
        }

        return config

    @abstractmethod
    def get_arguments(self, command: str, args: dict) -> list:
        """Return execution arguments for the specified command and arguments.

        Args:
            command: Command.
            args: Arguments.

        Returns:
            List of execution arguments.
        """

    def get_environment(self) -> dict:
        """Return environment considering the process environment."""
        env = os.environ.copy()
        env.update(self.config.get("environment", {}))
        return env

    def execute(self, command: str, args: dict | None = None) -> subprocess.Popen:
        """Execute program command with the specified arguments."""
        process = psutil.Popen(
            [self.config["executable"]] + self.get_arguments(command, args or {}),
            shell=False,
            cwd=self.config.get("workdir"),
            env=self.get_environment(),
        )

        return process
