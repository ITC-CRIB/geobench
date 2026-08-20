"""Python executor module."""

import json
import os
import shutil
import subprocess

from . import ExecutorInfo, ExecutorOption
from .program import ProgramExecutor


class PythonExecutor(ProgramExecutor):
    """Python executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            code="python",
            name="Python Script",
            description="Executes a Python script with arguments.",
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
            "venv": ExecutorOption(
                description="Virtual environment path",
                type=str,
            ),
        }

    @classmethod
    def get_python_path(cls) -> str:
        path = shutil.which("python") or shutil.which("python3")

        if path is None:
            raise FileNotFoundError("Python executable not found")

        return path

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

    @classmethod
    def get_python_metadata(cls, path: str | None = None) -> dict:
        if path is None:
            path = cls.get_python_path()

        code = (
            "import json;"
            "import platform;"
            "import sys;"
            "print(json.dumps({"
            '    "python_version": platform.python_version(),'
            '    "python_revision": platform.python_revision(),'
            '    "python_long_version": sys.version,'
            '    "python_implementation": platform.python_implementation(),'
            '    "python_compiler": platform.python_compiler(),'
            '    "python_build": ", ".join(platform.python_build()),'
            "}))"
        )

        try:
            result = subprocess.run(
                [path, "-c", code], capture_output=True, text=True, check=True
            )
            return json.loads(result.stdout)

        except subprocess.SubprocessError as err:
            raise RuntimeError(f"Error running python: {path}") from err

    def prepare_config(self):
        """Complete and validate the configuration options."""
        super().prepare_config()

        executable = self.config.get("executable")

        venv = self.config.get("venv")
        if venv:
            executable = os.path.join(
                venv, "Scripts/python.exe" if os.name == "nt" else "bin/python"
            )
            if not (os.path.isfile(executable) or os.path.islink(executable)):
                raise FileNotFoundError(
                    f"Python executable not found in virtual environment: {venv}"
                )

        if not executable:
            executable = self.get_python_path()

        if not self.is_python_executable(executable):
            raise RuntimeError(f"Invalid Python executable: {executable}")

        self.config["executable"] = executable
        self.metadata |= self.get_python_metadata(executable)

    def get_arguments(self, arguments: dict) -> list:
        """Return execution arguments for the specified arguments.

        Args:
            arguments: Arguments.

        Returns:
            List of execution arguments.

        Raises:
            FileNotFoundError: If Python script not found.
        """
        filename = self.config["filename"]

        if not os.path.isabs(self.config["filename"]) and self.config.get("workdir"):
            filename = os.path.join(self.config["workdir"], filename)

        if not os.path.isfile(filename):
            raise FileNotFoundError(f"Python script not found: {filename}")

        args = [filename] + self.get_cli_arguments(arguments)

        return args
