import dotenv
import os
import platform
import shlex
import subprocess
# replace unconditional winreg import and add helpers
import glob
import shutil
try:
    import winreg  # Windows only
except Exception:
    winreg = None  # type: ignore

from . import Executor


class QGISProcessExecutor(Executor):
    """QGIS Process Executor class."""

    @staticmethod
    def get_qgis_bin_path():
        """Returns QGIS executables directory path."""
        system = platform.system()

        if system == 'Windows':
            try:
                if winreg is not None:
                    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'QGIS Project\Shell\open\command') as key:
                        val, _ = winreg.QueryValueEx(key, None)
                        return os.path.dirname(shlex.split(val)[0])
            except FileNotFoundError:
                pass

            path = os.environ.get('OSGEO4W_ROOT')
            if path:
                return os.path.join(path, 'bin')

            path = os.environ.get('QGIS_PREFIX_PATH')
            if path:
                path = path.replace('\\', '/').split('/')
                if len(path) >= 2 and path[-2].lower() == 'apps' and path[-1].lower() == 'qgis':
                    path = path[:-2]
                return (os.sep.join(path + ['bin']))

        elif system == 'Linux':
            return '/usr/bin'

        elif system == 'Darwin':
            # 1) Respect explicit prefix if provided
            prefix = os.environ.get('QGIS_PREFIX_PATH')
            if prefix:
                cand = os.path.join(prefix, 'bin')
                if os.path.isdir(cand):
                    return cand

            # 2) If qgis_process is on PATH (Homebrew or symlink), use its directory
            qp = shutil.which('qgis_process')
            if qp:
                return os.path.dirname(os.path.realpath(qp))

            # 3) Look for official app bundles under /Applications starting with "QGIS"
            #    Include standard names first, then any QGIS*.app
            for app in sorted(glob.glob('/Applications/QGIS*.app'), reverse=True):
                cand = os.path.join(app, 'Contents', 'MacOS', 'bin')
                if os.path.isdir(cand):
                    return cand

            # 4) Common Homebrew bins (Apple Silicon and Intel)
            for hb in ('/opt/homebrew/bin', '/usr/local/bin'):
                if os.path.isfile(os.path.join(hb, 'qgis_process')):
                    return hb

        else:
            raise RuntimeError("Unsupported operating system.")

        raise RuntimeError("Cannot find QGIS installation path.")


    @staticmethod
    def find_executable(path: str, name: str) -> str | None:
        """Finds executable with the specified path and name.

        Args:
            path (str): Path of the executable.
            name (str): Name of the executable.

        Returns:
            Path of the executable if found, None otherwise.
        """
        if not os.path.isdir(path):
            return None

        system = platform.system()

        for filename in os.listdir(path):
            if not filename.startswith(name):
                continue

            if system == 'Windows':
                if filename.lower().endswith(('.exe', '.bat', '.cmd')):
                    return os.path.join(path, filename)

            else:
                path = os.path.join(path, filename)
                if os.access(path, os.X_OK):
                    return path

        return None


    @staticmethod
    def get_qgis_process_path() -> str:
        """Returns qgis_process executable path."""
        bin_path = __class__.get_qgis_bin_path()
        path = __class__.find_executable(bin_path, 'qgis_process')

        if not path:
            raise FileNotFoundError("qgis_process not found in {}.".format(bin_path))

        return path


    @staticmethod
    def get_qgis_environment() -> dict:
        """Returns QGIS environment variables."""
        bin_path = __class__.get_qgis_bin_path()

        environment = {}

        for file in os.listdir(bin_path):
            if file.endswith('.env'):
                environment = dotenv.dotenv_values(os.path.join(bin_path, file))
                break

        return environment


    def get_config(self) -> dict:
        """Returns executor configuration."""
        config = {}

        qgis_process_path = __class__.get_qgis_process_path()

        try:
            result = subprocess.run(
                [qgis_process_path, '--version'],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                raise RuntimeError("qgis_process failed with exit code {}.".format(result.returncode))

            config['executable'] = qgis_process_path
            config['environment'] = __class__.get_qgis_environment()
            config['versions'] = [line for line in result.stdout.splitlines() if line.strip()]

        except subprocess.SubprocessError as err:
            raise RuntimeError("Error running qgis_process.") from err

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