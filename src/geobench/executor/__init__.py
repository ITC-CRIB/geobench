import psutil
import time

from ..monitor import monitor_process


class Executor:
    """Executor class."""

    def __init__(self, scenario):
        """Initializes executor object.

        Args:
            scenario (Scenario): Scenario object.

        Raises:
            ValueError: if no executable found.
        """
        self.scenario = scenario
        self.config = self.get_config()

        if not self.config['executable']:
            raise ValueError("No executable found for the executor.")


    def get_config(self) -> dict:
        """Returns executor configuration."""
        raise NotImplementedError


    def get_arguments(self, command: str, args: dict) -> list:
        """Returns execution arguments for the specified command and arguments.

        Args:
            command (str): Command.
            args (dict): Arguments.

        Returns:
            List of execution arguments.
        """
        raise NotImplementedError


    def execute(self, args: list):
        """Executes executable with the specified arguments.

        Args:
            args (list): Arguments.
        """
        command = [self.config['executable']] + args

        out = {
            'start_time': time.time(),
            'finished': False,
            'success': False,
        }

        try:
            process = psutil.Popen(
                command,
                shell=False,
                cwd=self.scenario.workdir,
                env=self.config.get('environment', {})
            )
            out['pid'] = process.pid

            # Prepare energy configuration
            energy_config = {}
            if self.scenario.energy_api_url:
                energy_config['energy_api_url'] = self.scenario.energy_api_url
            if self.scenario.energy_api_timeout:
                energy_config['energy_api_timeout'] = self.scenario.energy_api_timeout

            metrics = monitor_process(process, energy_config=energy_config)

            out.update(metrics)

            out['finished'] = True
            out['success'] = (process.returncode == 0)

            if process.returncode:
                print(f"Command '{' '.join(command)}' failed with exit code {process.returncode}")

        except Exception as err:
            print(f"Command '{' '.join(command)}' failed with error: {err}")
            out['error'] = str(err)

        out['end_time'] = time.time()

        return out
