"""Shell executor module."""

import os
import platform

from . import ExecutorInfo, ExecutorOption
from .program import ProgramExecutor


class ShellExecutor(ProgramExecutor):
    """Shell executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            code="shell",
            name="Shell Script",
            description="Executes a shell script.",
        )

    @classmethod
    def get_options(cls) -> dict[str, ExecutorOption]:
        """Return executor options."""
        return super().get_options() | {
            "command": ExecutorOption(
                description="Shell command",
                type=str,
                positional=True,
                required=True,
            ),
        }

    def prepare_config(self, config: dict) -> None:
        """Complete and validate the configuration options."""
        super().prepare_config(config)

        if not config.get("executable"):
            system = platform.system()

            if system == "Windows":
                config["executable"] = os.environ.get("COMSPEC")

            else:
                config["executable"] = os.environ.get("SHELL")

    def get_arguments(self, arguments: dict) -> list:
        """Return execution arguments for the specified arguments.

        Args:
            arguments: Arguments.

        Returns:
            List of execution arguments.
        """
        args = []

        system = platform.system()

        if (
            system == "Windows"
            and os.path.basename(self.config["executable"]).lower() == "cmd.exe"
        ):
            args.append("/C")

        args.append(self.config["command"])
        args.extend(self.get_cli_arguments(arguments))

        return args

    def get_config_code(self) -> str:
        """Return a code identifying the configuration."""
        return os.path.basename(self.config["command"])
