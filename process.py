import psutil

def get_process_info():
    process_list = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
        try:
            process_info = proc.info
            process_list.append(process_info)
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

if __name__ == "__main__":
    main()