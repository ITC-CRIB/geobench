"""Function executor module."""

import os
import threading
from typing import Any

from . import Executor, ExecutorInfo, ExecutorOption


class FunctionExecutor(Executor):
    """Function executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            code="function",
            name="Function",
            description="Executes a Python function with arguments.",
        )

    @classmethod
    def get_options(cls) -> dict[str, ExecutorOption]:
        return super().get_options() | {
            "function": ExecutorOption(
                description="Function to be executed",
                type=callable,
            )
        }

    def __init__(self, config: dict | None = None, no_check: bool = False):
        """Initialize the function executor.

        Args:
            config: Optional configuration.
        """
        super().__init__(config, no_check=no_check)

        self.thread = None
        self.result = None
        self.exception = None

    def execute(self, arguments: dict | None = None) -> int:
        """Execute function with the specified arguments."""
        args, kwargs = {}, {}

        for key, val in (arguments or {}).items():
            try:
                args[int(key)] = val
            except (TypeError, ValueError):
                kwargs[key] = val

        args = [val for _, val in sorted(args.items())]

        self.result = None
        self.exception = None

        def _execute():
            try:
                self.result = self.config["function"](*args, **kwargs)
            except BaseException as exception:  # noqa: BLE001
                self.exception = exception

        self.thread = threading.Thread(target=_execute)
        self.thread.start()

        return os.getpid()

    def wait(self) -> Any:
        """Wait until execution ends.

        Returns:
            Return value of the function.

        Raises:
            RuntimeError: If function is not running.
            Exception: If function raises exception.
        """
        if not self.thread:
            raise RuntimeError("Function is not running")

        self.thread.join()

        if self.exception:
            raise self.exception

        return self.result
