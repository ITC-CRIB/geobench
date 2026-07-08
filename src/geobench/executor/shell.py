"""Shell executor module."""

import os
import platform

from . import ExecutorInfo
from .program import ProgramExecutor


class ShellExecutor(ProgramExecutor):
    """Shell executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            type="shell",
            name="Shell Script Executor",
            description="Executes a shell script.",
        )

    def get_config(self, args: dict) -> dict:
        """Return executor configuration considering the arguments.

        Args:
            args: Configuration arguments.
        """
        config = super().get_config(args)

        system = platform.system()

        if system == "Windows":
            shell = os.environ.get("COMSPEC")

        else:
            shell = os.environ.get("SHELL")

        config["executable"] = shell

        return config

    def get_arguments(self, command: str, args: dict) -> list:
        """Return execution arguments for the specified command and arguments.

        Args:
            command: Command.
            args: Arguments.

        Returns:
            List of execution arguments.
        """
        out = []

        system = platform.system()

        if (
            system == "Windows"
            and os.path.basename(self.config["executable"]).lower() == "cmd.exe"
        ):
            out.append("/C")

        out.append(command)
        out.extend(self.get_cli_arguments(args))

        return out
