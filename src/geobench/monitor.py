"""Monitoring module."""

import logging
import threading
import time

from .collector import Collector, Process, get_collector, get_process

logger = logging.getLogger(__name__)


class Monitor(threading.Thread):
    """Thread-based monitor class."""

    @classmethod
    def get_collector(
        cls, collector: str | dict, process: Process | None = None
    ) -> Collector:
        if isinstance(collector, str):
            type, config = collector, {}

        elif isinstance(collector, dict):
            type, config = collector.get("type"), collector.get("config", {})

        return get_collector(type, config, process)

    def __init__(
        self,
        collectors: list[str | dict | Collector],
        name: str | None = None,
        duration: float = 0.0,
        interval: float = 1.0,
        process: Process | None = None,
        stop_event: threading.Event | None = None,
    ):
        """Initialize monitor.

        Args:
            collectors: List of collectors.
            name: Code of the monitor.
            duration: Monitoring duration, in seconds (default = unlimited).
            interval: Interval between each sample, in seconds (default = 1.0).
            process: Optional process to monitor.
            stop_event: Optional stop event.
        """
        super().__init__(daemon=True)

        if process:
            process = get_process(process)

        self.name = name
        self.duration = duration
        self.interval = interval
        self.collectors = [
            collector
            for item in collectors
            for collector in [
                item
                if isinstance(item, Collector)
                else self.get_collector(item, process)
            ]
        ]
        self.process = process
        self.stop_event = stop_event
        self.done = False

    def run(self):
        """Run the data collection loop."""
        self.start_time = None
        self.end_time = None
        self.step = 0
        self.done = False

        logger.debug(
            "[%s] Monitor started (interval: %f s, duration: %f s)",
            self.name,
            self.interval,
            self.duration,
        )

        while True:
            now = time.time()
            if not self.start_time:
                self.start_time = now

            if self.duration and (now - self.start_time) >= self.duration:
                self.done = True

            elif self.process and not self.process.is_running():
                self.done = True
                self.end_time = now
                break

            elif self.stop_event and self.stop_event.is_set():
                self.done = True

            for collector in self.collectors:
                collector.collect()

            if self.done:
                self.end_time = now
                break

            time.sleep(self.interval)
            self.step += 1

        logger.debug(
            "[%s] Monitor stopped (%d samples)",
            self.name,
            self.step + 1,
        )

    def get_data(self) -> dict:
        """Get collected data.

        Returns:
            Dictionary of collected data.
        """
        if not self.done:
            raise RuntimeError("Monitoring not completed")

        out = {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": {
                "target": self.duration,
                "actual": self.end_time - self.start_time,
            },
            "interval": {
                "target": self.interval,
                "actual": (self.end_time - self.start_time) / self.step,
            },
            "data": {},
        }

        for collector in self.collectors:
            out["data"][collector.code] = collector.get_data()

        return out
