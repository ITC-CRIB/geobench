"""QGIS process executor module."""

import subprocess

from . import ExecutorInfo, ExecutorOption
from .qgis import QGISExecutor


class QGISProcessExecutor(QGISExecutor):
    """QGIS process executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            code="qgis-process",
            name="QGIS Process",
            description="Executes a QGIS algorithm.",
        )

    @classmethod
    def get_options(cls) -> dict[str, ExecutorOption]:
        """Return executor options."""
        return super().get_options() | {
            "algorithm": ExecutorOption(
                description="QGIS algorithm id",
                type=str,
                required=True,
                positional=True,
            ),
        }

    def prepare_config(self):
        """Complete and validate the configuration options."""
        super().prepare_config()

        qgis_process_path = (
            self.config.get("executable") or self.get_qgis_process_path()
        )

        try:
            result = subprocess.run(
                [qgis_process_path, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"qgis_process failed with exit code: {result.returncode}"
                )

        except subprocess.SubprocessError as err:
            raise RuntimeError("Error running qgis_process") from err

        self.config["executable"] = qgis_process_path

        self.metadata |= {
            "qgis_versions": [
                line for line in result.stdout.splitlines() if line.strip()
            ]
        }

    def get_arguments(self, arguments: dict) -> list:
        """Return execution arguments for the specified arguments.

        Args:
            arguments: Arguments.

        Returns:
            List of execution arguments.
        """
        args = ["run", self.config["algorithm"]] + self.get_cli_arguments(arguments)

        return args

    def get_help(self) -> str:
        """Return help content."""
        result = subprocess.run(
            [self.config["executable"]]
            + (
                ["help", self.config["algorithm"]]
                if self.config.get("algorithm")
                else ["list"]
            ),
            env=self.get_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        return result.stderr or result.stdout

    def get_config_code(self) -> str:
        """Return a code identifying the configuration."""
        return self.config["algorithm"]
