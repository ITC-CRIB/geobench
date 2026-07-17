"""Function executor module."""

import os
import threading

from . import ExecutorInfo, Executor


class FunctionExecutor(Executor):
    """Function executor class."""

    @classmethod
    def get_info(cls) -> ExecutorInfo:
        return ExecutorInfo(
            code="function",
            name="Function Executor",
            description="Executes a Python function with arguments.",
        )

    def __init__(self, config: dict | None = None):
        """Initialize the function executor.

        Args:
            config: Optional configuration.
        """
        super().__init__(config)

        self.thread = None

    def get_config(self, args: dict) -> dict:
        """Return executor configuration considering the arguments.

        Args:
            args: Configuration arguments.
        """
        return {}

    def execute(self, command: callable, args: dict | None = None) -> int:
        """Execute function with the specified arguments."""
        pargs, kwargs = {}, {}

        for key, val in (args or {}).items():
            try:
                pargs[int(key)] = val
            except (TypeError, ValueError):
                kwargs[key] = val

        pargs = [val for _, val in sorted(pargs.items())]

        self.thread = threading.Thread(target=command, args=pargs, kwargs=kwargs)
        self.thread.start()

        return os.getpid()

    def wait(self):
        """Wait until execution ends."""
        if not self.thread:
            raise RuntimeError("Function is not running")

        self.thread.join()
