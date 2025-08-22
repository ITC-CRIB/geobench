import os
import platform
import subprocess

from . import Executor


class QGISProcessExecutor(Executor):
    """QGIS Process Executor class."""

    def _get_qgis_path(self):
        """Returns QGIS path."""
        path = os.getenv('QGIS_PATH')
        if path:
            return path

        system = platform.system()

        if system == 'Windows':
            # FIXME: Drive is not always C:\
            # FIXME: Program files are not always located under 'Program Files'
            return r'C:\\Program Files\\QGIS'

        elif system == 'Linux':
            return '/usr/bin'

        elif system == 'Darwin':
            return '/Applications/QGIS.app/Contents/MacOS'

        else:
            raise RuntimeError("Unsupported operating system.")


    def _find_executable(self, path: str, name: str) -> str | None:
        """Finds executable with the specified path and name.

        Args:
            path (str): Path of the executable.
            name (str): Name of the executable.

        Returns:
            Path of the executable if found, None otherwise.
        """
        extensions = ('.exe', '.bat', '.cmd', '.com', '.ps1')

        if not os.path.isdir(path):
            return None

        system = platform.system()

        for filename in os.listdir(path):
            if not filename.startswith(name):
                continue

            if system == 'Windows':
                if filename.lower().endswith(extensions):
                    return os.path.join(path, filename)

            else:
                fullpath = os.path.join(path, filename)
                if os.access(fullpath, os.X_OK):
                    return fullpath

        return None


    def _get_qgis_process_path(self, qgis_path: str) -> str:
        """Returns qgis_process executable path.

        Args:
            qgis_path (str): QGIS path.

        Returns:
            qgis_process path if found, None otherwise.
        """
        system = platform.system()

        if system == 'Windows':
            bin_path =  os.path.join(qgis_path, 'bin')

        elif system == 'Linux':
            bin_path = qgis_path

        elif system == 'Darwin':
            bin_path = os.path.join(qgis_path, 'bin')

        else:
            raise RuntimeError("Unsupported operating system.")

        path = self._find_executable(bin_path, 'qgis_process')

        if not path:
            raise FileNotFoundError("qgis_process not found in {}.".format(bin_path))

        return path


    def get_config(self) -> dict:
        """Returns executor configuration."""
        config = {}

        qgis_path = self._get_qgis_path()
        qgis_process_path = self._get_qgis_process_path(qgis_path)

        try:
            result = subprocess.run(
                [qgis_process_path, '--version'],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                raise RuntimeError(f"'qgis_process --version' command failed with exit code {result.returncode}.")

            config['executable'] = qgis_process_path
            config['versions'] = [line for line in result.stdout.splitlines() if line.strip()]

        except subprocess.SubprocessError as err:
            raise RuntimeError("Error running 'qgis_process --version'.") from err

        return config


    def get_arguments(self, command: str, args: dict) -> list:
        """Returns execution arguments for the specified command and arguments.

        Args:
            command (str): Command.
            args (dict): Arguments.
        
        Returns:
            List of execution arguments.
        """
        out = ['run', command]

        for key, val in args.items():
            out.append(f"--{key}={val}")

        return out