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

    # Monitor the process with the given PID
    def monitor_process(self, pid):
        # Flag to check if the process is found
        is_process_found = False
        try:
            # Get the process using the pid
            process = psutil.Process(pid)
            # Get process name
            process_name = process.name()
            is_process_found = True
            start_time = datetime.now()
            cpu_percents = []
            memory_percents = []
            
            # Initialize the process metrics if recording logs
            if self.record_logs:
                with self.lock:
                    self.process_metrics[pid] = {'samples': []}
            else:
                with self.lock:
                    self.process_metrics[pid] = {}

            # Monitor the process while it is running
            while process.is_running():
                recording_time = datetime.now()
                # Get the CPU and memory usage of the process
                cpu_percent = process.cpu_percent(interval=self.interval)
                memory_percent = process.memory_percent()

                # Append the usage data to the lists
                cpu_percents.append(cpu_percent)
                memory_percents.append(memory_percent)

                # Record the logs if required
                if self.record_logs:
                    with self.lock:
                        self.process_metrics[pid]['samples'].append({
                            'timestamp': recording_time,
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory_percent,
                        })

        except psutil.NoSuchProcess:
            # Handle the case where the process has terminated
            print(f"Process {pid} has terminated.")
        finally:
            if is_process_found:
                # Calculate the running time and average CPU and memory usage
                running_time = datetime.now() - start_time
                avg_cpu_percent = statistics.mean(cpu_percents) if cpu_percents else 0
                avg_memory_percent = statistics.mean(memory_percents) if memory_percents else 0

                with self.lock:
                    # Update the process metrics with the calculated values
                    self.process_metrics[pid].update({
                        'name': process_name,
                        'running_time': running_time.total_seconds(),
                        'avg_cpu_percent': avg_cpu_percent,
                        'avg_memory_percent': avg_memory_percent
                    })
                

    # Monitor the system-wide CPU and memory usage
    def monitor_system(self, parent_pid):
        # Lists to store the system-wide CPU and memory usage data
        sys_cpu_usage = []
        sys_mem_info = []
        # Get the power function for the specific OS
        power_function = self.get_power_function()

        try:
            # Get the main process
            main_process = psutil.Process(parent_pid)

            while main_process.is_running():
                # Define tasks to get per-CPU usage of system-wide 
                per_cpu_percent_task = self.executor.submit(self.get_cpu_usage_per_cpu)

                # All monitoring tasks
                all_tasks = [per_cpu_percent_task]

                # Check if power function exists for specific OS
                if power_function is not None:
                    power_task = self.executor.submit(power_function)
                    all_tasks.append(power_task)
                
                # Wait all tasks to complete
                as_completed(all_tasks)
                # Get tasks result
                per_cpu_percent = per_cpu_percent_task.result()
                # Get power usage if power function exists
                power_usage = None
                if power_function is not None:
                    power_usage = power_task.result()
                
                # Calculate average system-wide CPU usage given CPU usages for all core
                all_cores_avg_cpu_percent = sum(per_cpu_percent) / len(per_cpu_percent)
                # Get the current system-wide memory information
                memory_snapshot = psutil.virtual_memory()
                memory_info = self._convert_named_tuple_to_dict(memory_snapshot)
                # Create a dictionary to store the log data
                log = {
                    "sys_cpu" : all_cores_avg_cpu_percent,
                    "sys_per_cpu": per_cpu_percent,
                    "sys_mem" : memory_info,
                    "time" : time.time(),
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
        self.start_monitoring(parent_process)

    # Start monitoring the process and the system, and check for new child processes
    def start_monitoring(self, parent_process: Process):
        parent_pid = parent_process.pid
        
        # Add the parent process PID to the monitored list
        with self.lock:
            self.monitored_pids.append(parent_pid)
        
        # Start monitoring the parent process and the system
        self.executor.submit(self.monitor_process, parent_pid)
        self.executor.submit(self.monitor_system, parent_pid)

        # Continuously check for new child processes while the parent process is running
        while parent_process.poll() is None:
            try:
                # Get the parent process and its children
                parent = psutil.Process(parent_pid)
                children = parent.children(recursive=True)
                for child in children:
                    with self.lock:
                        # If a new child process is found, start monitoring it
                        if child.pid not in self.monitored_pids:
                            self.monitored_pids.append(child.pid)
                            self.executor.submit(self.monitor_process, child.pid)
            except psutil.NoSuchProcess:
                break

        # Wait for all monitoring tasks to complete before shutting down the executor
        self.executor.shutdown(wait=True)
        # Calculate the final statistics
        self._calculate_statistics()

    # Calculate statistics for monitored processes
    def _calculate_statistics(self):
        # Initialize total CPU and memory usage percentages
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

    def print_metrics(self):
        for pid, metrics in self.process_metrics.items():
            print(f"Process {pid} metrics:")
            print(f"     {metrics}")
            # print(f"  Running Time: {metrics['running_time']:.2f}s")
            # print(f"  Average CPU: {metrics['avg_cpu_percent']:.2f}%")
            # print(f"  Average Memory: {metrics['avg_memory_percent']:.2f}%")
            # print("  Samples:")
            # for sample in metrics['samples']:
            #     print(f"    Timestamp: {sample['timestamp']}, CPU: {sample['cpu_percent']:.2f}%, "
            #           f"Memory: {sample['memory_percent']:.2f}%")

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