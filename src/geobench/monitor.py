import asyncio
import platform
import psutil
import statistics
import sys
import threading
import time

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from multiprocessing.dummy import Process


import logging
logger = logging.getLogger(__name__)


class ProcessMonitor:
    """Process monitor class."""

    def __init__(self, interval: float=1.0):
        """Initializes process monitor object.

        Args:
            interval (float): Interval between each sample (s) (default = 1.0).
        """
        self.interval = interval
        # Dictionary to store metrics for each monitored process
        self.process_metrics = {}
        # List to store the PIDs of monitored processes
        self.process_pids = []
        # List to store system-wide logs metrics
        self.system_metrics = []
        # Dictionary to store overall metrics
        self.metrics = {}
        # Lock to ensure thread-safe operations
        self.lock = threading.Lock()
        # Thread pool executor to manage concurrent monitoring tasks
        self.executor = ThreadPoolExecutor(max_workers=10)  # Adjust max_workers as needed
        # List to store the PIDs of terminated processes
        self.terminated_pids = []


    async def get_cpu_usage_per_cpu(self):
        """Gets CPU usage per cpu."""
        return psutil.cpu_percent(interval=self.interval, percpu=True)


    def _calculate_average_memory_info(self, memory_data):
        """Calculates average available memory information metrics."""
        # Initialize a defaultdict to hold sums for each field.
        sum_data = defaultdict(float)
        field_counts = len(memory_data)

        # Iterate over each memory snapshot and sum the values for each field.
        for memory_snapshot in memory_data:
            for field, value in memory_snapshot.items():
                sum_data[field] += value

        # Calculate the average value for each field.
        avg_data = {field: sum_value / field_counts for field, sum_value in sum_data.items()}

        return avg_data


    async def _monitor_single_process(self, process):
        try:
            cpu_percent = process.cpu_percent(interval=self.interval)
            memory_percent = process.memory_percent()

            recording_time = time.time()

            self.process_metrics[process.pid]['logs'].append({
                'timestamp': recording_time,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
            })
        except psutil.NoSuchProcess:
            self.terminated_pids.append(process.pid)


    async def start_monitoring(self, parent_process):
        parent_pid = parent_process.pid

        # Add the parent process PID to the monitored list
        self.process_pids.append(parent_pid)

        # Start monitoring the parent process and the system
        self.executor.submit(self.start_system_monitoring, parent_pid)

        parent_pid = parent_process.pid

        self.process_metrics[parent_pid] = {
            'name': parent_process.name(),
            'command': parent_process.cmdline(),
            'logs': []
        }

        while parent_process.poll() is None:
            # Check if the parent process has terminated. Parent process may have been terminated but still detected as running.
            if parent_pid not in self.terminated_pids:
                # Monitor the parent process
                all_tasks = [self._monitor_single_process(parent_process)]
                # Get the children of the parent process
                children = parent_process.children(recursive=True)
                # Monitor all children of the parent process
                for child in children:
                    child_pid = child.pid
                    # Monitor a newly detected child process
                    if child_pid not in self.process_metrics:
                        # Create a data structure to store metrics for the child process
                        self.process_metrics[child_pid] = {
                            'name': child.name(),
                            'command': child.cmdline(),
                            'logs': []
                        }
                    # Check if the child process has terminated. A process may have terminated but still detected as part of child processes.
                    if child_pid not in self.terminated_pids:
                        all_tasks.append(self._monitor_single_process(child))

                # Wait for all tasks to complete
                await asyncio.gather(*all_tasks)
            else:
                break

        # Shutdown the executor
        self.executor.shutdown(wait=True)
        print("Monitoring completed.")

        # Calculate statistics for monitored processes
        print("Calculating statistics.")
        self._calculate_statistics()


    def start_system_monitoring(self, parent_pid):
        """Helper to call async monitor_system function."""
        asyncio.run(self.monitor_system(parent_pid))


    async def monitor_system(self, parent_pid):
        """Monitors the system-wide CPU and memory usage."""
        # Lists to store the system-wide CPU and memory usage data
        sys_cpu_usage = []
        sys_mem_info = []

        try:
            # Get the main process
            main_process = psutil.Process(parent_pid)

            while main_process.is_running():
                # Create tasks for async execution
                tasks = []

                # Task to get per-CPU usage of system-wide
                cpu_task = self.get_cpu_usage_per_cpu()
                tasks.append(cpu_task)

                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)

                # Get tasks results
                per_cpu_percent = results[0]

                # Calculate average system-wide CPU usage given CPU usages for all core
                all_cores_avg_cpu_percent = sum(per_cpu_percent) / len(per_cpu_percent)

                # Get the current system-wide memory information
                memory_snapshot = psutil.virtual_memory()
                memory_info = vars(memory_snapshot)

                # Create a dictionary to store the log data
                log = {
                    "sys_cpu": all_cores_avg_cpu_percent,
                    "sys_per_cpu": per_cpu_percent,
                    "sys_mem": memory_info,
                    "time": time.time(),
                }

                # Append the log data to the list
                self.system_metrics.append(log)

                # Append the usage data to the lists for average calculation of system-wide metric
                sys_cpu_usage.append(all_cores_avg_cpu_percent)
                sys_mem_info.append(memory_info)

        except psutil.NoSuchProcess:
            print("System monitoring stopped.")

        finally:
            # Calculate the average CPU and memory usage
            self.metrics["system_avg_cpu"] = sum(sys_cpu_usage) / len(sys_cpu_usage) if sys_cpu_usage else 0
            # Calculate the average system-wide memory info
            self.metrics["system_avg_mem"] = self._calculate_average_memory_info(sys_mem_info) if sys_mem_info else 0


    def monitor(self, process):
        asyncio.run(self.start_monitoring(process))


    def _calculate_statistics(self):
        """Calculates statistics for monitored processes."""
        # Calculate the average running time for each process
        for pid, process_metric in self.process_metrics.items():
            # Get the metrics samples for the process
            metrics_samples = process_metric['logs']
            running_time = 0

            # Calculate running time given at least 2 samples
            if len(metrics_samples) > 1:
                running_time = metrics_samples[-1]['timestamp'] - metrics_samples[0]['timestamp']

            # Calculate average CPU and memory usage given at least 1 sample
            avg_cpu_percent = statistics.mean([sample['cpu_percent'] for sample in metrics_samples]) if len(metrics_samples) > 0 else 0
            avg_memory_percent = statistics.mean([sample['memory_percent'] for sample in metrics_samples]) if len(metrics_samples) > 0 else 0

            # Update the process metrics with the calculated statistics
            with self.lock:
                self.process_metrics[pid].update({
                    'running_time': running_time,
                    'avg_cpu_percent': avg_cpu_percent,
                    'avg_memory_percent': avg_memory_percent
                })

        # Calculate average CPU and memory usage percentages of related processes
        total_cpu_percent = 0
        total_memory_percent = 0
        # Get the number of monitored processes
        num_processes = len(self.process_metrics)

        # Iterate over the metrics of each monitored process
        for proc_metrics in self.process_metrics.values():
            # Accumulate the average CPU usage percentage
            total_cpu_percent += proc_metrics['avg_cpu_percent']
            # Accumulate the average memory usage percentage
            total_memory_percent += proc_metrics['avg_memory_percent']

        # Calculate the average CPU usage percentage across all processes
        process_related_avg_cpu_percent = total_cpu_percent / num_processes if num_processes > 0 else 0
        # Calculate the average memory usage percentage across all processes
        process_related_avg_memory_percent = total_memory_percent / num_processes if num_processes > 0 else 0

        # Store the calculated average CPU usage in the overall metrics
        self.metrics["process_avg_cpu"] = process_related_avg_cpu_percent
        # Store the calculated average memory usage in the overall metrics
        self.metrics["process_avg_mem"] = process_related_avg_memory_percent
        # Store system-wide logs in the overall metrics
        self.metrics["system_metrics"] = self.system_metrics
        # Store process-specific metrics in the overall metrics
        self.metrics["process_metrics"] = self.process_metrics


    def get_metrics(self):
        return self.metrics
