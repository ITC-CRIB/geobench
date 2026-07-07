"""GDAL executor module."""

import glob
import os
import shlex
import shutil
import subprocess

try:
    import winreg
except Exception:
    winreg = None

import dotenv

from . import ExecutorInfo
from .program import ProgramExecutor


class GDALExecutor(ProgramExecutor):
    """GDAL executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            type="gdal",
            name="GDAL Executor",
            description="Executes a GDAL command with arguments.",
        )

    @staticmethod
    def get_gdal_bin_path():
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

    @staticmethod
    def get_gdal_path() -> str:
        """Return GDAL executable path.

        Raises:
            FileNotFoundError: If GDAL executable not found.
        """
        bin_path = __class__.get_gdal_bin_path()
        path = __class__.find_executable(bin_path, "gdal")

        if not path:
            raise FileNotFoundError(f"gdal not found in: {bin_path}")

        return path

    @staticmethod
    def get_gdal_environment() -> dict:
        """Return GDAL environment variables."""
        bin_path = __class__.get_gdal_bin_path()
        
        env = {}

        for file in os.listdir(bin_path):
            if file.endswith(".env"):
                env = dotenv.dotenv_values(os.path.join(bin_path, file))
                break

        return env

    def get_config(self, args: dict) -> dict:
        """Return executor configuration considering the arguments.

        Args:
            args: Configuration arguments.

        Raises:
            RuntimeError: If GDAL fails.
        """
        config = super().get_config(args)

        gdal_path = __class__.get_gdal_path()

        try:
            result = subprocess.run(
                [gdal_path, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"GDAL failed with exit code: {result.returncode}"
                )

            config["executable"] = gdal_path
            config["environment"] = __class__.get_gdal_environment()
            config["versions"] = [
                line for line in result.stdout.splitlines() if line.strip()
            ]

        except subprocess.SubprocessError as err:
            raise RuntimeError("Error running GDAL") from err

        return config

    def get_arguments(self, command: str, args: dict) -> list:
        """Return execution arguments for the specified command and arguments.

        Args:
            command: Command.
            args: Arguments.

        Returns:
            List of execution arguments.
        """
        out = [command]

        for key, val in args.items():
            out.append(f"--{key}={val}")

        return out

    def get_help(self, command: str) -> str:
        """Return help content for the GDAL command.
        
        Args:
            command: GDAL command.
        """
        result = subprocess.run(
            [self.config["executable"], command, "help"],
            env=self.get_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        return result.stdout
