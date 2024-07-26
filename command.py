import sys
import error
import subprocess
import threading
import time

from recording import monitor_usage

def decode_qgis_command(command_str):
    parts = command_str.split()

    if len(parts) > 3:
        result = {"command": parts[0] + " " + parts[1] + " " + parts[2]}
        
        for part in parts[3:]:
            if part.startswith('--'):
                key, value = part.lstrip('--').split('=', 1)
                result[key] = value
        return result
    else:
        raise error.WrongQGISCommandError

def encode_qgis_command(command_dict):
    # Extract the base command
    command = command_dict['command']
    
    # Extract and format the parameters
    params = []
    for key, value in command_dict.items():
        if key != 'command':
            params.append(f"--{key}={value}")
    
    # Join the command and parameters into a single string
    command_str = command + ' ' + ' '.join(params)
    return command_str

def check_requirement(command_type="qgis-command"):
    if command_type == "qgis-command":
        try:
            # Try to run 'qgis_process' with the '--help' flag
            result = subprocess.run(['qgis_process', '--help'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                print("qgis_process command exists.")
        except FileNotFoundError:
            print("qgis_process command not found. Please ensure QGIS is installed and the command is available in the system PATH.")
            sys.exit(1)
        except subprocess.CalledProcessError:
            raise Exception("qgis_process command exists but returned an error.")

def execute_command(command):
    results = {"finished": False}
    monitor_thread = threading.Thread(target=monitor_usage, args=(results,))
    monitor_thread.start()
    
    exec_start_time = time.time()
    try:
        subprocess.run(command, shell=True, check=True)
        results["success"] = True
    except subprocess.CalledProcessError as e:
        results["success"] = False
        print(f"Command failed with {e.returncode}")
    results["finished"] = True
    monitor_thread.join()
    exec_end_time = time.time()
    results["start_time"] = exec_start_time
    results["end_time"] =  exec_end_time

    return results