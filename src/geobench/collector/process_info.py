"""Process info collector module."""

from . import CollectorInfo, ProcessCollector


class ProcessInfoCollector(ProcessCollector):
    """Collector for process information."""

    @classmethod
    def get_info(cls) -> CollectorInfo:
        """Return collector information."""
        return CollectorInfo(
            code="process_info",
            name="Process Information Collector",
            description="Collects process information.",
        )

    def collect(self) -> dict:
        """Collect process information.

        Returns:
            Dictionary containing process information.
        """
        return {
            "pid": self.process.pid,
            "parent_pid": self.process.ppid(),
            "name": self.process.name(),
            "executable": self.process.exe(),
            "command": self.process.cmdline(),
            "environment": self.process.environ(),
            "create_time": self.process.create_time(),
        }
