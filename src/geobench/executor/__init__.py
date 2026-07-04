import psutil
import time
import traceback

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

        if not self.config["executable"]:
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
        command = [self.config["executable"]] + args

        out = {
            "start_time": time.time(),
            "finished": False,
            "success": False,
        }

        try:
            process = psutil.Popen(
                command,
                shell=False,
                cwd=self.scenario.workdir,
                env=self.config.get("environment", {}),
            )
            out["pid"] = process.pid

            # Prepare monitoring configuration
            # Support both legacy energy_config and new data_sources
            energy_config = {}
            data_sources = None

            if hasattr(self.scenario, "data_sources") and self.scenario.data_sources:
                # New multi-threaded mode with data_sources
                data_sources = self.scenario.data_sources
            else:
                # Legacy mode with energy_config
                if self.scenario.energy_api_url:
                    energy_config["energy_api_url"] = self.scenario.energy_api_url
                if self.scenario.energy_api_timeout:
                    energy_config["energy_api_timeout"] = (
                        self.scenario.energy_api_timeout
                    )

            metrics = monitor_process(
                process,
                energy_config=energy_config if energy_config else None,
                data_sources=data_sources,
            )

            out.update(metrics)

            out["finished"] = True
            out["success"] = process.returncode == 0

            if process.returncode:
                print(
                    f"Command '{' '.join(command)}' failed with exit code {process.returncode}"
                )

        except Exception as err:
            print(f"Command '{' '.join(command)}' failed with error: {err}")
            print("Full stack trace:")
            traceback.print_exc()
            out["error"] = str(err)

        out["end_time"] = time.time()

        return out
