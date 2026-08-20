"""Function executor module."""

import os
import threading

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

    def execute(self, arguments: dict | None = None) -> int:
        """Execute function with the specified arguments."""
        args, kwargs = {}, {}

        for key, val in (arguments or {}).items():
            try:
                args[int(key)] = val
            except (TypeError, ValueError):
                kwargs[key] = val

        args = [val for _, val in sorted(args.items())]

        self.thread = threading.Thread(
            target=self.config["function"], args=args, kwargs=kwargs
        )
        self.thread.start()

        return os.getpid()

    def wait(self):
        """Wait until execution ends."""
        if not self.thread:
            raise RuntimeError("Function is not running")

        self.thread.join()
