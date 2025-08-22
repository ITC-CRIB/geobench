import importlib
import jinja2
import os
import platform
import subprocess
import tempfile

from .qgis_process import QGISProcessExecutor


class QGISPythonExecutor(QGISProcessExecutor):
    """QGIS Python executor class."""

    def _get_qgis_python_path(self, qgis_path: str) -> str | None:
        """Returns QGIS Python executable path.

        Args:
            qgis_path (str): QGIS path.

        Returns:
            QGIS Python executable path if found, None otherwise.
        """
        system = platform.system()

        if system == 'Windows':
            qgis_apps_path = os.path.join(qgis_path, 'apps')
            matches = [
                entry.name for entry in os.scandir(qgis_apps_path)
                if entry.is_dir() and entry.name.lower().startswith('python')
            ]
            if not matches:
                return None
            bin_path =  os.path.join(matches[0], qgis_apps_path)

        elif system == 'Linux':
            bin_path = qgis_path

        elif system == 'Darwin':
            bin_path = os.path.join(qgis_path, 'bin')

        else:
            raise RuntimeError("Unsupported operating system.")

        path = self._find_executable(bin_path, 'python3')
        if not path:
            raise FileNotFoundError("QGIS Python executable not found.")

        return path


    def get_config(self) -> dict:
        """Returns executor configuration."""
        config = {}

        qgis_path = self._get_qgis_path()
        qgis_python_path = self._get_qgis_python_path(qgis_path)

        try:
            result = subprocess.run(
                [qgis_python_path, '--version'],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                raise RuntimeError(f"QGIS Python '--version' command failed with exit code {result.returncode}.")

            config['executable'] = qgis_python_path

        except subprocess.SubprocessError as err:
            raise RuntimeError("Error running QGIS Python '--version'.") from err

        return config


    def get_arguments(self, command: str, args: dict) -> list:
        """Returns execution arguments for the specified command and arguments.

        Args:
            command (str): Command.
            args (dict): Arguments.

        Returns:
            List of execution arguments.
        """
        qgis_code = f'processing.run("{command}", {args})'

        with importlib.resources.path(__package__, 'templates') as template_dir:
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
            template = env.get_template('qgis_python.j2')
            script = template.render(
                qgis_path=self._get_qgis_path(),
                qgis_bin_path=os.path.dirname(self.config['executable']),
                qgis_code=qgis_code,
            )

        with tempfile.NamedTemporaryFile(mode='w+t', delete=False) as file:
            temp.write(script)

        return [temp.name]
