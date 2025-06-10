from collections import defaultdict
from pathlib import Path
import platform
import sys
import time
import psutil
import subprocess
from datetime import datetime
import statistics
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple

class ProcessMonitor:
    # Initialize the ProcessMonitor class
    def __init__(self, record_logs=False, interval=0.5):
        # Flag to determine if logs should be recorded
        self.record_logs = record_logs
        # Interval between each monitoring sample in seconds
        self.interval = interval
        # Dictionary to store metrics for each monitored process
        self.process_metrics = {}
        # Dictionary to store logs for each monitored process
        self.process_metrics_logs = {}
        # List to store the PIDs of monitored processes
        self.monitored_pids = []
        # List to store system-wide logs metrics
        self.system_logs_metrics = []
        # Dictionary to store overall metrics
        self.metrics = {}
        # Lock to ensure thread-safe operations
        self.lock = asyncio.Lock()
        # Event loop for asyncio
        self.loop = None

        self.sys_cpu_usage = []
        self.sys_mem_info = []

    # Get CPU usage per cpu
    def get_cpu_usage_per_cpu(self):
        return psutil.cpu_percent(interval=self.interval, percpu=True)
    
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

    async def monitor_process(self, pid):
        """
        Monitor a single process continuously while it's running.
        Returns False if the process no longer exists, True otherwise.
        """
        try:
            # Get the process using the pid
            process = psutil.Process(pid)
            
            # Check if this is the first time monitoring this process
            if pid not in self.process_metrics:
                # Get process name
                process_name = process.name()
                
                # Initialize the process metrics
                async with self.lock:
                    self.process_metrics_logs[pid] = {
                        'start_time': datetime.now(),
                        'cpu_percents': [],
                        'memory_percents': [],
                    }
                    if self.record_logs:
                        self.process_metrics[pid] = {
                            'name': process_name,
                            'samples': [],
                            'running_time': 0,
                            'avg_cpu_percent': 0,
                            'avg_memory_percent': 0
                        }
                    else:
                        self.process_metrics[pid] = {
                            'name': process_name,
                            'running_time': 0,
                            'avg_cpu_percent': 0,
                            'avg_memory_percent': 0
                        }
            
            # Monitor the process while it's still running
            while process.is_running():
                # Get the CPU and memory usage of the process
                cpu_percent = process.cpu_percent(interval=self.interval)  # Non-blocking
                memory_percent = process.memory_percent()
                
                # Update metrics
                async with self.lock:
                    # Append the usage data to the lists
                    self.process_metrics_logs[pid]['cpu_percents'].append(cpu_percent)
                    self.process_metrics_logs[pid]['memory_percents'].append(memory_percent)
                    
                    # Record the logs if required
                    if self.record_logs:
                        # Record current time
                        recording_time = datetime.now()
                        self.process_metrics[pid]['samples'].append({
                            'timestamp': recording_time,
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory_percent,
                        })
            with self.lock:
                self._finalize_process_metrics(pid)
                self.monitored_pids.remove(pid)
                print(f"Process {pid} finalized")
            return True
        except psutil.NoSuchProcess:
            print(f"Process {pid} not exists")
            return False
            

    def _finalize_process_metrics(self, pid):
        """Finalize metrics for a process that has terminated."""
        # async with self.lock:
        if pid in self.process_metrics_logs:
            metrics_logs = self.process_metrics_logs[pid]
            # Calculate the running time and average CPU and memory usage
            running_time = datetime.now() - metrics_logs['start_time']
            avg_cpu_percent = statistics.mean(metrics_logs['cpu_percents'])
            avg_memory_percent = statistics.mean(metrics_logs['memory_percents'])
            
            # Update the process metrics with the calculated values
            self.process_metrics[pid].update({
                'running_time': running_time.total_seconds(),
                'avg_cpu_percent': avg_cpu_percent,
                'avg_memory_percent': avg_memory_percent
            })

    async def monitor_system(self, parent_process):
        """
        Monitor system metrics for one cycle.
        """
        while parent_process.is_running():
            # Get per-CPU usage directly
            per_cpu_percent = self.get_cpu_usage_per_cpu()
            
            # Get power usage if power function exists
            power_function = self.get_power_function()
            power_usage = None
            if power_function is not None:
                power_usage = power_function()
            
            # Calculate average system-wide CPU usage
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
            self.sys_cpu_usage.append(all_cores_avg_cpu_percent)
            self.sys_mem_info.append(memory_info)
        
        return True

    async def start_monitoring(self, parent_process):
        print("Start monitoring routines")
        parent_pid = parent_process.pid
        
        # Add the parent process PID to the monitored list
        async with self.lock:
            self.monitored_pids.append(parent_pid)
            
        # Initialize system monitoring data
        self.sys_cpu_usage = []
        self.sys_mem_info = []
        tasks = []
        
        # Monitor system metrics
        tasks.append(asyncio.create_task(self.monitor_system(parent_process)))

        # Monitor parent process
        tasks.append(asyncio.create_task(self.monitor_process(parent_pid)))

        # Main monitoring loop
        while parent_process.is_running():
            children = parent_process.children(recursive=True)
            
            # Check for new child processes to add
            for child in children:
                if child.pid not in self.monitored_pids:
                    tasks.append(asyncio.create_task(self.monitor_process(child.pid)))
                    self.monitored_pids.append(child.pid)
                    print(f"Started monitoring new child process: {child.pid}")
            
            # # Check for processes that no longer exist to remove
            # for pid in current_pids:
            #     try:
            #         process = psutil.Process(pid)
            #         if not process.is_running():
            #             async with self.lock:
            #                 if pid in self.monitored_pids:
            #                     self.monitored_pids.remove(pid)
            #                     print(f"Removed terminated process: {pid} from monitoring")
            #     except psutil.NoSuchProcess:
            #         async with self.lock:
            #             if pid in self.monitored_pids:
            #                 self.monitored_pids.remove(pid)
            #                 # Calculate final metrics for the terminated process
            #                 self._finalize_process_metrics(pid)
            #                 print(f"Removed non-existent process: {pid} from monitoring")
        
        print("Waiting for all processes to finish")
        await asyncio.gather(*tasks)
        print("All processes finished")
        
        print("Collected metrics")
        print(self.process_metrics)

        print("Calculate system-wide metrics")
        # Calculate system-wide metrics
        self.metrics["system_avg_cpu"] = sum(self.sys_cpu_usage) / len(self.sys_cpu_usage)
        self.metrics["system_avg_mem"] = self._calculate_average_memory_info(self.sys_mem_info)
        
        print("Calculate the final statistics")
        # Calculate the final statistics
        self._calculate_statistics()

    def run_monitoring(self, parent_process):
        """
        Entry point to start the monitoring process using asyncio.
        This method creates a new event loop and runs the start_monitoring coroutine.
        """
        # Create and set the event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            # Run the start_monitoring coroutine
            self.loop.run_until_complete(self.start_monitoring(parent_process))
        finally:
            # Close the event loop
            self.loop.close()

    def _calculate_statistics(self):

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
    parent_process = subprocess.Popen(command, shell=True)
    monitor.run_monitoring(parent_process)
    running_time = datetime.now() - start_time
    print(f"Total running time: {running_time.total_seconds()}s")
    print("Monitoring complete.")
    metrics = monitor.get_metrics()
    print(metrics)

if __name__ == "__main__":
    main()