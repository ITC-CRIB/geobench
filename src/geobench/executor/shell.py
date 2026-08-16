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
            code="shell",
            name="Shell Script Executor",
            description="Executes a shell script.",
        )

    def prepare_config(self, config: dict) -> None:
        """Complete the configuration options."""
        super().prepare_config(config)

        if not config.get("executable"):
            system = platform.system()

            if system == "Windows":
                config["executable"] = os.environ.get("COMSPEC")

            else:
                config["executable"] = os.environ.get("SHELL")

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
