"""QGIS executor module."""

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

from .program import ProgramExecutor


class QGISExecutor(ProgramExecutor):
    """QGIS executor class."""

    @classmethod
    def get_qgis_bin_path(cls):
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

    @classmethod
    def get_qgis_process_path(cls, bin_path: str | None = None) -> str:
        """Return qgis_process executable path.

        Raises:
            FileNotFoundError: If qgis_process executable not found.
        """
        if bin_path is None:
            bin_path = cls.get_qgis_bin_path()

        path = cls.find_executable(bin_path, "qgis_process")

        if not path:
            raise FileNotFoundError(f"qgis_process not found in: {bin_path}")

        return path

    @classmethod
    def get_qgis_python_path(cls, bin_path: str | None = None) -> str:
        """Return QGIS python executable path.

        Raises:
            FileNotFoundError: If python executable not found.
        """
        if bin_path is None:
            bin_path = cls.get_qgis_bin_path()

        path = cls.find_executable(bin_path, "python")

        if not path:
            raise FileNotFoundError(f"QGIS python not found in: {bin_path}")

        return path

    @classmethod
    def get_qgis_versions(cls, bin_path: str | None = None) -> list[str]:
        qgis_process_path = cls.get_qgis_process_path(bin_path)

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

        versions = [line for line in result.stdout.splitlines() if line.strip()]

        return versions

    @classmethod
    def get_qgis_environment(cls, bin_path: str | None = None) -> dict:
        """Return QGIS environment variables."""
        if bin_path is None:
            bin_path = cls.get_qgis_bin_path()

        for file in os.listdir(bin_path):
            if file.endswith(".env"):
                return dotenv.dotenv_values(os.path.join(bin_path, file))

        return {}

    def get_environment(self) -> dict:
        """Return environment considering the process environment."""
        return super().get_environment() | self.get_qgis_environment(
            os.path.dirname(self.config["executable"])
        )
