import psutil
import platform

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

def main():
    process_list = get_process_info()
    print(f"{'PID':<10} {'Name':<25} {'Username':<20} {'CPU%':<10} {'Memory%':<10} {'Status':<15}")
    print("="*90)
    for proc in process_list:
        print(proc)
        # print(f"{proc['pid']:<10} {proc['name']:<25} {proc['username']:<20} {proc['cpu_percent']:<10} {proc['memory_percent']:<10} {proc['status']:<15}")

def print_system_config():
    sys_config = get_system_info()
    print(sys_config)

def print_process_info():
    proc_info = get_process_info()
    print(proc_info)

if __name__ == "__main__":
    # main()
    print_system_config()
    # print_process_info()