"""Program executor module."""

from abc import abstractmethod
import subprocess

import psutil

from . import Executor


class ProgramExecutor(Executor):
    """Program executor class."""

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

    def execute(self, command: str, args: dict | None = None) -> subprocess.Popen:
        """Execute program command with the specified arguments."""
        process = psutil.Popen(
            [self.config["executable"]] + self.get_arguments(command, args or {}),
            shell=False,
            cwd=self.config.get("workdir"),
            env=self.config.get("environment", {}),
        )

        return process
