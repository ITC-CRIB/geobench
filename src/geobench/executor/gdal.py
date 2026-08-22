"""GDAL executor module."""

import glob
import os
import shlex
import shutil
import subprocess

try:
    import winreg
except ImportError:
    winreg = None

import dotenv

from . import ExecutorInfo, ExecutorOption
from .program import ProgramExecutor


class GDALExecutor(ProgramExecutor):
    """GDAL executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            code="gdal",
            name="GDAL",
            description="Executes a GDAL command.",
        )

    @classmethod
    def get_options(cls) -> dict[str, ExecutorOption]:
        """Return executor options."""
        return super().get_options() | {
            "command": ExecutorOption(
                description="GDAL command",
                type=str,
                required=True,
                positional=True,
            ),
            "subcommand": ExecutorOption(
                description="Subcommand of the GDAL command",
                type=str,
                positional=True,
            ),
        }

    @classmethod
    def get_gdal_bin_path(cls):
        """Return GDAL executable directory path.

        Raises:
            RuntimeError: If GDAL cannot be found.
        """
        # Check the default gdal
        path = shutil.which("gdal")
        if path:
            return os.path.dirname(os.path.realpath(path))

        # Check Windows registry
        if winreg is not None:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CLASSES_ROOT, r"QGIS Project\Shell\open\command"
                ) as key:
                    val, _ = winreg.QueryValueEx(key, None)
                    return os.path.dirname(shlex.split(val)[0])
            except FileNotFoundError:
                pass

        # Check OSGeo4W path
        path = os.environ.get("OSGEO4W_ROOT")
        if path:
            return os.path.join(path, "bin")

        # Check common folders
        for path in ("/usr/bin", "/usr/local/bin", "/opt/homebrew/bin"):
            if os.path.isfile(os.path.join(path, "gdal")):
                return path

        # Check app bundles under /Applications starting with "QGIS"
        for app in sorted(glob.glob("/Applications/QGIS*.app"), reverse=True):
            path = os.path.join(app, "Contents", "MacOS", "bin")
            if os.path.isdir(path):
                return path

        # Use explicit prefix if provided
        path = os.environ.get("QGIS_PREFIX_PATH")
        if path:
            path = path.replace("\\", "/").split("/")
            if (
                len(path) >= 2
                and path[-2].lower() == "apps"
                and path[-1].lower() == "qgis"
            ):
                path = path[:-2]
            path = os.sep.join(path + ["bin"])
            if os.path.isdir(path):
                return path

        raise RuntimeError("Cannot find GDAL path")

    @classmethod
    def get_gdal_path(cls) -> str:
        """Return GDAL executable path.

        Raises:
            FileNotFoundError: If GDAL executable not found.
        """
        bin_path = cls.get_gdal_bin_path()
        path = cls.find_executable(bin_path, "gdal")

        if not path:
            raise FileNotFoundError(f"gdal not found in: {bin_path}")

        return path

    @classmethod
    def get_gdal_environment(cls) -> dict:
        """Return GDAL environment variables."""
        bin_path = cls.get_gdal_bin_path()

        env = {}

        for file in os.listdir(bin_path):
            if file.endswith(".env"):
                env = dotenv.dotenv_values(os.path.join(bin_path, file))
                break

        return env

    def prepare_config(self):
        """Complete and validate the configuration options."""
        super().prepare_config()

        gdal_path = self.config.get("executable") or self.get_gdal_path()

        try:
            result = subprocess.run(
                [gdal_path, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(f"GDAL failed with exit code: {result.returncode}")

        except subprocess.SubprocessError as err:
            raise RuntimeError("Error running GDAL") from err

        self.config["executable"] = gdal_path

        self.metadata |= {
            "versions": [line for line in result.stdout.splitlines() if line.strip()],
        }

    def get_arguments(self, arguments: dict) -> list:
        """Return execution arguments for the specified arguments.

        Args:
            arguments: Arguments.

        Returns:
            List of execution arguments.
        """
        args = (
            [self.config["command"]]
            + ([self.config["subcommand"]] if self.config.get("subcommand") else [])
            + self.get_cli_arguments(arguments)
        )

        return args

    def get_environment(self) -> dict:
        """Return environment considering the process environment."""
        return super().get_environment() | self.get_gdal_environment()

    def get_help(self) -> str:
        """Return help content."""
        result = subprocess.run(
            [self.config["executable"]]
            + ([self.config["command"]] if self.config.get("command") else [])
            + ([self.config["subcommand"]] if self.config.get("subcommand") else [])
            + ["--help"],
            env=self.get_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        return result.stdout

    def get_config_code(self) -> str:
        """Return a code identifying the configuration."""
        return self.config["command"] + (
            (":" + self.config["subcommand"]) if self.config.get("subcommand") else ""
        )
