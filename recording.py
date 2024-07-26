import time
import platform
import psutil
import subprocess

def get_system_info():
    # OS information
    system_info = {
        "os": {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
    }

    # CPU information
    system_info["cpu"] = {
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "max_frequency": psutil.cpu_freq().max,
        "min_frequency": psutil.cpu_freq().min,
        "current_frequency": psutil.cpu_freq().current,
        "usage": psutil.cpu_percent(interval=1)
    }

    # Memory information
    svmem = psutil.virtual_memory()
    system_info["memory"] = {
        "total": svmem.total // (1024 * 1024),
        "available": svmem.available // (1024 * 1024),
        "used": svmem.used // (1024 * 1024),
        "percentage": svmem.percent
    }

    # Disk information
    disk_info = []
    partitions = psutil.disk_partitions()
    for partition in partitions:
        partition_info = {
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "fstype": partition.fstype
        }
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            partition_info.update({
                "total_size": partition_usage.total // (1024 * 1024),
                "used": partition_usage.used // (1024 * 1024),
                "free": partition_usage.free // (1024 * 1024),
                "percentage": partition_usage.percent
            })
        except PermissionError:
            # this can be caught due to the disk that isn't ready
            partition_info.update({
                "total_size": "PermissionError",
                "used": "PermissionError",
                "free": "PermissionError",
                "percentage": "PermissionError"
            })
        disk_info.append(partition_info)
    
    system_info["disk"] = disk_info

    return system_info

def get_process_info():
    process_list = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
        try:
            # Get process info using psutil
            proc_info = proc.info
            pid = proc_info['pid']
            name = proc_info['name']
            cpu_usage = proc_info['cpu_percent']
            memory_usage = proc_info['memory_percent']
            
            # Disk usage (I/O)
            try:
                io_counters = proc.io_counters()
                read_bytes = io_counters.read_bytes // (1024 * 1024)  # Convert bytes to MB
                write_bytes = io_counters.write_bytes // (1024 * 1024)  # Convert bytes to MB
            except (psutil.AccessDenied, AttributeError):
                read_bytes = write_bytes = 0

            process_list.append({
                'pid': pid,
                'name': name,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'read_bytes': read_bytes,
                'write_bytes': write_bytes
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return process_list

def _record_process_info(duration=30, interval=1):
    process_info = {}

    for _ in range(int(duration / interval)):
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                proc_info = proc.info
                pid = proc_info['pid']
                name = proc_info['name']
                cpu_usage = proc_info['cpu_percent']
                memory_usage = proc_info['memory_percent']

                # Disk usage (I/O)
                try:
                    io_counters = proc.io_counters()
                    read_bytes = io_counters.read_bytes // (1024 * 1024)  # Convert bytes to MB
                    write_bytes = io_counters.write_bytes // (1024 * 1024)  # Convert bytes to MB
                except (psutil.AccessDenied, AttributeError):
                    read_bytes = write_bytes = 0

                if pid not in process_info:
                    process_info[pid] = {
                        'name': name,
                        'cpu_usage': [],
                        'memory_usage': [],
                        'read_bytes': [],
                        'write_bytes': [],
                        'username': proc_info.get('username', 'N/A')
                    }
                
                if cpu_usage is not None:
                    process_info[pid]['cpu_usage'].append(cpu_usage)
                if memory_usage is not None:
                    process_info[pid]['memory_usage'].append(memory_usage)
                if read_bytes is not None:
                    process_info[pid]['read_bytes'].append(read_bytes)
                if write_bytes is not None:
                    process_info[pid]['write_bytes'].append(write_bytes)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        time.sleep(interval)

    return process_info

def _average(sum, len):
    if len > 0:
        return sum / len
    return 0

def _calculate_average_usage(process_info):
    average_info = []

    for pid, info in process_info.items():
        avg_cpu =  _average( sum(info['cpu_usage']) , len(info['cpu_usage']) )
        avg_memory = _average( sum(info['memory_usage']) , len(info['memory_usage']) )
        avg_read_bytes = _average( sum(info['read_bytes']) , len(info['read_bytes']) )
        avg_write_bytes = _average( sum(info['write_bytes']) , len(info['write_bytes']) )

        average_info.append({
            'pid': pid,
            'name': info['name'],
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'avg_read_bytes': avg_read_bytes,
            'avg_write_bytes': avg_write_bytes,
            'username': info['username']
        })

    # Sort by average CPU usage in descending order
    average_info.sort(key=lambda x: x['avg_memory_usage'], reverse=True)
    return average_info

# Record running process for specific duration, then calculate the average CPU and memory usage
def record_process_info(duration=30):
    process_info = _record_process_info(duration=duration, interval=1)
    average_info = _calculate_average_usage(process_info)

    return average_info

# Perform baseline monitoring for a specific duration. The function return the average CPU and memory usage.
def monitor_baseline(duration=15):
    results = {}
    cpu_usage = []
    mem_usage = []

    # Define the start time
    start_time = time.time()

    # Define the duration for which the code should run (in seconds)
    duration = 15

    # Loop until the specified duration has passed
    while time.time() - start_time < duration:
        cpu_usage.append(psutil.cpu_percent(interval=1))
        mem_usage.append(psutil.virtual_memory().percent)
        time.sleep(0.1)
    results["avg_cpu"] = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
    results["avg_mem"] = sum(mem_usage) / len(mem_usage) if mem_usage else 0
    return results

# Perform monitoring during benchmark. The function return the average CPU and memory usage.
def monitor_usage(results):
    cpu_usage = []
    mem_usage = []
    # Loop until execution is finished
    while not results.get("finished"):
        cpu_usage.append(psutil.cpu_percent(interval=1))
        mem_usage.append(psutil.virtual_memory().percent)
    results["avg_cpu"] = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
    results["avg_mem"] = sum(mem_usage) / len(mem_usage) if mem_usage else 0

def get_qgis_plugins():
    # Execute the shell command
    result = subprocess.run(['qgis_process', 'plugins'], capture_output=True, text=True)

    # Capture the output
    output = result.stdout

    # Initialize an empty list to store plugin names
    plugin_names = []

    # Parse the output to extract plugin names
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('*'):
            plugin_name = line.split()[1]
            plugin_names.append(plugin_name)

    return plugin_names

def get_qgis_config():
    # Execute the shell command
    result = subprocess.run(['qgis_process', '--version'], capture_output=True, text=True)

    # Capture the output
    version = result.stdout

    # Split the output text into lines
    lines = version.splitlines()
    
    # Initialize an empty list to store the relevant lines
    parsed_lines = []
    
    # Iterate over each line
    for line in lines:
        line = line.strip()
        # Skip lines that contain warnings or errors
        if "Cannot" not in line:
            parsed_lines.append(line)
    
    return parsed_lines

def record_software_config():
    software_config = get_qgis_config()
    return software_config

def main():
    process_list = record_process_info()
    for proc in process_list:
        print(proc)
        # print(f"{proc['pid']:<10} {proc['name']:<25} {proc['username']:<20} {proc['cpu_percent']:<10} {proc['memory_percent']:<10} {proc['status']:<15}")

def print_system_config():
    sys_config = get_system_info()
    print(sys_config)

def print_process_info():
    proc_info = record_process_info()
    print(proc_info)

if __name__ == "__main__":
    # main()
    # print_system_config()
    print_process_info()