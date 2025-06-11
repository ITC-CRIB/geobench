from collections import defaultdict
from multiprocessing.dummy import Process
from pathlib import Path
import platform
import sys
import time
import psutil
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import threading
import asyncio

class ProcessMonitor:
    # Initialize the ProcessMonitor class
    def __init__(self, record_logs=False, interval=0.5):
        # Flag to determine if logs should be recorded
        self.record_logs = record_logs
        # Interval between each monitoring sample in seconds
        self.interval = interval
        # Dictionary to store metrics for each monitored process
        self.process_metrics = {}
        # List to store the PIDs of monitored processes
        self.monitored_pids = []
        # List to store system-wide logs metrics
        self.system_logs_metrics = []
        # Dictionary to store overall metrics
        self.metrics = {}
        # Lock to ensure thread-safe operations
        self.lock = threading.Lock()
        # Thread pool executor to manage concurrent monitoring tasks
        self.executor = ThreadPoolExecutor(max_workers=10)  # Adjust max_workers as needed
        # List to store the PIDs of terminated processes
        self.terminated_pids = []

    # Get CPU usage per cpu
    def get_cpu_usage_per_cpu(self):
        return psutil.cpu_percent(interval=self.interval, percpu=True)
    
    # Async version of get_cpu_usage_per_cpu
    async def get_cpu_usage_per_cpu_async(self):
        return self.get_cpu_usage_per_cpu()
    
    def get_powermetrics_data(self, duration=1000):
        try:
            # Run powermetrics command and capture output
            powermetrics_cmd = f"sudo powermetrics -s cpu_power,gpu_power -i {duration} -n 1"
            powermetrics_output = subprocess.check_output(powermetrics_cmd, shell=True, text=True, stderr=subprocess.STDOUT)

            # Initialize CPU and GPU power consumption to 0
            cpu_power=0
            gpu_power=0
            # Parse output to extract CPU and GPU power consumption
            output_lines = powermetrics_output.splitlines()
            # Extract CPU and GPU power consumption from the output
            for line in output_lines:
                if "CPU Power:" in line:
                    cpu_power = float(line.split(":")[1].strip().split()[0])
                elif "GPU Power:" in line:
                    gpu_power = float(line.split(":")[1].strip().split()[0])
            # Return the CPU and GPU power consumption
            return {
                "cpu_power": cpu_power,
                "gpu_power": gpu_power
            }
        except subprocess.CalledProcessError as e:
            print(f"Error running powermetrics: {e.output}")
            return None

    # Async version of get_powermetrics_data
    async def get_powermetrics_data_async(self, duration=1000):
        return self.get_powermetrics_data(duration)

    def get_power_function(self):
        """
        Determines the appropriate power metrics function based on the operating system.

        Returns:
            function: A reference to the `get_powermetrics_data` method if the operating system is macOS (Darwin).
                  Returns None for other operating systems.
        """
        os_type = platform.system()
        # Check if the operating system is macOS (Darwin)
        if os_type == "Darwin":
            # Return the powermetrics function for macOS
            return self.get_powermetrics_data
        else:
            return None
    
    # Get async power function
    def get_async_power_function(self):
        """
        Determines the appropriate async power metrics function based on the operating system.

        Returns:
            function: A reference to the `get_powermetrics_data_async` method if the operating system is macOS (Darwin).
                  Returns None for other operating systems.
        """
        os_type = platform.system()
        # Check if the operating system is macOS (Darwin)
        if os_type == "Darwin":
            # Return the async powermetrics function for macOS
            return self.get_powermetrics_data_async
        else:
            return None
    
    # Convert named tuples to dictionaries
    def _convert_named_tuple_to_dict(self, named_tuple):
        return {field: getattr(named_tuple, field) for field in named_tuple._fields}
    
    # Calculate average available memory information metrics
    def _calculate_average_memory_info(self, memory_data):
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

            recording_time = datetime.now().timestamp()

            self.process_metrics[process.pid]['samples'].append({
                'timestamp': recording_time,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
            })
        except psutil.NoSuchProcess:
            self.terminated_pids.append(process.pid)
            # print(f"DEBUG: Skip monitoring for {process.pid}. Running status: {process.is_running()}")

    async def start_monitoring_with_asyncio(self, parent_process):
        parent_pid = parent_process.pid
        
        # Add the parent process PID to the monitored list
        self.monitored_pids.append(parent_pid)
        
        # Start monitoring the parent process and the system
        self.executor.submit(self.start_system_monitoring, parent_pid)

        parent_pid = parent_process.pid

        self.process_metrics[parent_pid] = {
            'name': parent_process.name(),
            'command': parent_process.cmdline(),
            'samples': []
        }
        # print(f"DEBUG: Parent process ID: {parent_pid}")

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
                            'samples': []
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
        print("Monitoring completed. Calculating statistics...")
        # Calculate statistics for monitored processes
        self._calculate_statistics()

    # Helper to call async monitor_system function
    def start_system_monitoring(self, parent_pid):
        asyncio.run(self.monitor_system(parent_pid))

    # Monitor the system-wide CPU and memory usage
    async def monitor_system(self, parent_pid):
        # Lists to store the system-wide CPU and memory usage data
        sys_cpu_usage = []
        sys_mem_info = []
        # Get the async power function for the specific OS
        power_function = self.get_async_power_function()

        try:
            # Get the main process
            main_process = psutil.Process(parent_pid)

            while main_process.is_running():
                # Create tasks for async execution
                tasks = []
                
                # Task to get per-CPU usage of system-wide
                cpu_task = self.get_cpu_usage_per_cpu_async()
                tasks.append(cpu_task)

                # Check if power function exists for specific OS
                if power_function is not None:
                    power_task = power_function()
                    tasks.append(power_task)
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)
                
                # Get tasks results
                per_cpu_percent = results[0]
                
                # Get power usage if power function exists
                power_usage = None
                if power_function is not None:
                    power_usage = results[1]
                
                # Calculate average system-wide CPU usage given CPU usages for all core
                all_cores_avg_cpu_percent = sum(per_cpu_percent) / len(per_cpu_percent)
                # Get the current system-wide memory information
                memory_snapshot = psutil.virtual_memory()
                memory_info = self._convert_named_tuple_to_dict(memory_snapshot)
                # Create a dictionary to store the log data
                log = {
                    "sys_cpu": all_cores_avg_cpu_percent,
                    "sys_per_cpu": per_cpu_percent,
                    "sys_mem": memory_info,
                    "time": time.time(),
                }
                if power_usage is not None:
                    log.update(power_usage)
                # Append the log data to the list
                self.system_logs_metrics.append(log)
                # Append the usage data to the lists for average calculation of system-wide metric
                sys_cpu_usage.append(all_cores_avg_cpu_percent)
                sys_mem_info.append(memory_info)

        except psutil.NoSuchProcess:
            print(f"System monitoring stopped.")
        finally:
            # Calculate the average CPU and memory usage
            self.metrics["system_avg_cpu"] = sum(sys_cpu_usage) / len(sys_cpu_usage) if sys_cpu_usage else 0
            # Calculate the average system-wide memory info
            self.metrics["system_avg_mem"] = self._calculate_average_memory_info(sys_mem_info) if sys_mem_info else 0

    # Run the command and start monitoring the process and the system
    def run(self, command):
        parent_process = subprocess.Popen(command, shell=True)
        asyncio.run(self.start_monitoring_with_asyncio(parent_process))

    def run_monitoring(self, parent_process):
        asyncio.run(self.start_monitoring_with_asyncio(parent_process))

    # Calculate statistics for monitored processes
    def _calculate_statistics(self):
        # Calculate the average running time for each process
        for pid, process_metric in self.process_metrics.items():
            # Get the metrics samples for the process
            metrics_samples = process_metric['samples']
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
        self.metrics["log_data"] = self.system_logs_metrics        
        # Store process-specific metrics in the overall metrics
        self.metrics["process_metrics"] = self.process_metrics
    
    def get_metrics(self):
        return self.metrics

def main():
    if len(sys.argv) != 2:
        print("Usage: python process_tracker.py <path_to_heavy_processes.py>")
        sys.exit(1)

    script_path = Path(sys.argv[1])
    if not script_path.is_file():
        print(f"Error: The file '{script_path}' does not exist.")
        sys.exit(1)

    python_executable = sys.executable
    command = [python_executable, str(script_path)]

    print(f"Monitoring: {' '.join(command)}")

    monitor = ProcessMonitor()
    start_time = datetime.now()
    monitor.run(' '.join(command))
    running_time = datetime.now() - start_time
    print(f"Total running time: {running_time.total_seconds()}s")
    print("Monitoring complete.")
    metrics = monitor.get_metrics()
    print(metrics)

if __name__ == "__main__":
    main()