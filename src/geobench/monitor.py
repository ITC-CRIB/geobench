import asyncio
import platform
import psutil
import statistics
import sys
import time


import logging
logger = logging.getLogger(__name__)


class ProcessMonitor:
    """Process monitor class."""

    def __init__(self, process, interval: float=1.0):
        """Initializes process monitor object.

        Args:
            process: Process.
            interval (float): Interval between each sample (s) (default = 1.0).
        """
        self.process = process
        self.interval = interval


    def get_process_info(self, process) -> dict:
        return {
            'pid': process.pid,
            'name': process.name(),
            'command': process.cmdline(),
            'metrics': [],
        }


    async def get_process_metrics(self, process):
        try:
            self.processes[process.pid]['metrics'].append({
                'step': self.step,
                'timestamp': time.time(),
                'cpu_percent': process.cpu_percent(interval=self.interval),
                'memory_percent': process.memory_percent(),
                'num_threads': process.num_threads(),
            })

        except psutil.NoSuchProcess:
            self.done.append(process.pid)


    async def get_system_metrics(self):
        self.system.append({
            'step': self.step,
            'timestamp': time.time(),
            'cpu_percent': psutil.cpu_percent(interval=self.interval, percpu=True),
            'memory_usage': psutil.virtual_memory()._asdict(),
        })


    def monitor(self):
        return asyncio.run(self._monitor())


    async def _monitor(self):
        self.step = 0
        self.processes = {}
        self.system = []
        self.done = []

        self.processes[self.process.pid] = self.get_process_info(self.process)

        while True:
            status = self.process.poll()
            if status is not None or self.process.pid in self.done:
                break

            self.step += 1

            tasks = []
            tasks.append(self.get_system_metrics())
            tasks.append(self.get_process_metrics(self.process))

            for child in self.process.children(recursive=True):
                if child.pid in self.done:
                    continue

                if child.pid not in self.processes:
                    self.processes[child.pid] = self.get_process_info(child)

                tasks.append(self.get_process_metrics(child))

            await asyncio.gather(*tasks)

        out = {
            'system': self.system,
            'processes': self.processes,
        }

        return out
