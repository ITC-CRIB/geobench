"""Executor module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache
import importlib
import inspect
import pkgutil
import time
import traceback

import psutil

from ..monitor import monitor_process

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorInfo:
    """Metadata describing a collector."""

    type: str
    name: str
    description: str


class Executor(ABC):
    """Executor class."""

    @classmethod
    @abstractmethod
    def get_info(cls) -> ExecutorInfo:
        """Return executor information."""

    def __init__(self, scenario: "Scenario"):
        """Initialize the executor.

        Args:
            scenario: Scenario to be executed.

        Raises:
            ValueError: if no executable is found.
        """
        self.scenario = scenario
        self.config = self.get_config()

        if not self.config["executable"]:
            raise ValueError("No executable found for the executor")

    @abstractmethod
    def get_config(self) -> dict:
        """Return the executor configuration."""

    @abstractmethod
    def get_arguments(self, command: str, args: dict) -> list:
        """Return execution arguments for the specified command and arguments.

        Args:
            command: Command.
            args: Arguments.

        Returns:
            List of execution arguments.
        """

    def execute(self, args: list) -> dict:
        """Run the executor with the specified arguments.

        Args:
            args: List of arguments.

        Returns:
            Dictionary of execution results:

            - start_time (float):  Start time in seconds since the Epoch.
            - end_time (float): End time in seconds since the Epoch.
            - finished (bool): True if finished without exceptions, otherwise False.
            - success (bool): True if finished without returncode, otherwise False.
            - pid (int): Process id if created successfully (optional).
            - returncode (int): Return code if not successful (optional).
            - error (str): Error message if finished with exception (optional).
            - Attributes provided by the monitor_process() method.
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

            metrics = monitor_process(
                process,
                telemetry=self.scenario.telemetry,
            )

            out.update(metrics)

            out["finished"] = True
            out["success"] = process.returncode == 0

            if process.returncode:
                print(
                    f"Command '{' '.join(command)}' failed with exit code: {process.returncode}"
                )
                out["returncode"] = process.returncode

        except Exception as err:
            print(f"Command '{' '.join(command)}' failed with error: {err}")
            print("Full stack trace:")
            traceback.print_exception(err)
            out["error"] = str(err)

        out["end_time"] = time.time()

        return out


@cache
def get_executors() -> dict[str, Executor]:
    """Return dictionary of available collectors."""
    executors = {}

    for _, name, _ in pkgutil.iter_modules([__path__[0]]):
        module = importlib.import_module(f".{name}", f"{Executor.__module__}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Executor) and cls is not Executor:
                if not cls.__abstractmethods__:
                    type = cls.get_info().type
                    executors[type] = cls
                else:
                    logger.debug(f"{cls} has abstract methods, skipping")

    return executors
