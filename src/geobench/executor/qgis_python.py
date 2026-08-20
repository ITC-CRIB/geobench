"""QGIS Python executor module."""

import os
import subprocess
import tempfile

import jinja2

from . import ExecutorInfo, ExecutorOption
from .qgis import QGISExecutor


class QGISPythonExecutor(QGISExecutor):
    """QGIS Python executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            code="qgis-python",
            name="QGIS Python Script",
            description="Executes a QGIS Python script.",
        )

    @classmethod
    def get_options(cls) -> dict[str, ExecutorOption]:
        """Return executor options."""
        return super().get_options() | {
            "filename": ExecutorOption(
                description="Script filename",
                type=str,
                required=True,
                positional=True,
            ),
        }

    def prepare_config(self) -> None:
        """Complete and validate the configuration options."""

        qgis_python_path = self.config.get("executable") or self.get_qgis_python_path()

        try:
            result = subprocess.run(
                [qgis_python_path, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"QGIS python failed with exit code: {result.returncode}"
                )

        except subprocess.SubprocessError as err:
            raise RuntimeError("Error running QGIS python") from err

        self.config["executable"] = qgis_python_path

        self.metadata |= {
            "versions": self.get_qgis_versions(os.path.dirname(qgis_python_path)),
        }

    def get_arguments(self, arguments: dict) -> list:
        """Return execution arguments for the specified arguments.

        Args:
            args: Arguments.

        Returns:
            List of execution arguments.
        """
        with open(self.config["filename"], "r", encoding="utf-8") as file:
            qgis_code = file.read()

        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
        template = env.get_template("qgis_python.j2")
        script = template.render(
            qgis_path=os.path.dirname(self.get_qgis_bin_path()),
            qgis_bin_path=os.path.dirname(self.config["executable"]),
            qgis_code=qgis_code,
            **arguments,
        )

        with tempfile.NamedTemporaryFile(
            mode="w+t", delete=False, encoding="utf-8"
        ) as file:
            file.write(script)

        return [file.name]
