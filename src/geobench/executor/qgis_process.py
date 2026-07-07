"""QGIS process executor module."""

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


class QGISProcessExecutor(ProgramExecutor):
    """QGIS process executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            type="qgis-process",
            name="QGIS Process Executor",
            description="Executes a qgis_process command with arguments.",
        )

    @staticmethod
    def get_qgis_bin_path():
        """Return QGIS executable directory path.

        Raises:
            RuntimeError: If QGIS installation cannot be found.
        """
        # Check the default qgis_process
        path = shutil.which("qgis_process")
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
            if os.path.isfile(os.path.join(path, "qgis_process")):
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

        raise RuntimeError("Cannot find QGIS installation path")

    @staticmethod
    def get_qgis_process_path() -> str:
        """Return qgis_process executable path.

        Raises:
            FileNotFoundError: If qgis_process executable not found.
        """
        bin_path = __class__.get_qgis_bin_path()
        path = __class__.find_executable(bin_path, "qgis_process")

        if not path:
            raise FileNotFoundError(f"qgis_process not found in: {bin_path}")

        return path

    @staticmethod
    def get_qgis_environment() -> dict:
        """Return QGIS environment variables."""
        bin_path = __class__.get_qgis_bin_path()

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
            RuntimeError: If qgis_process fails.
        """
        config = super().get_config(args)

        qgis_process_path = __class__.get_qgis_process_path()

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

            config["executable"] = qgis_process_path
            config["environment"] = __class__.get_qgis_environment()
            config["versions"] = [
                line for line in result.stdout.splitlines() if line.strip()
            ]

        except subprocess.SubprocessError as err:
            raise RuntimeError("Error running qgis_process") from err

        return config

    def get_arguments(self, command: str, args: dict) -> list:
        """Return execution arguments for the specified command and arguments.

        Args:
            command: Command.
            args: Arguments.

        Returns:
            List of execution arguments.
        """
        out = ["run", command]

        for key, val in args.items():
            out.append(f"--{key}={val}")

        return out

    def get_help(self, command: str) -> str:
        """Return help content for the qgis_process algorithm.
        
        Args:
            command: qgis_process algorithm.
        """
        result = subprocess.run(
            [self.config["executable"], "help", command],
            env=self.get_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        return result.stdout
