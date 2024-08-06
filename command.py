import sys
import error
import subprocess
import threading
import time
import os
import ast
import re
import platform

from recording import monitor_usage

def decode_qgis_command(command_str):
    parts = command_str.split()

    if len(parts) > 3:
        result = { 
            "command":  parts[1] + " " + parts[2]
        }
        
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

def _extract_parameters_from_code(code_snippet):
    try:
        # Use regex to find the dictionary part in the code
        pattern = re.compile(r"processing.run\([^,]+, ({[^}]+})\)")
        match = pattern.search(code_snippet)
        if match:
            param_str = match.group(1)
            return param_str
        else:
            return None
    except Exception as e:
        print(f"Error when extracting parameter from Python program: {e}")
        sys.exit(1)

def _decode_parameters(parameter_str):
    try:
        # Decode the string into a dictionary
        param_dict = ast.literal_eval(parameter_str)
        return param_dict
    except Exception as e:
        print(f"Error when decoding parameter from Python program: {e}")
        sys.exit(1)

def _encode_parameters(param_dict):
    try:
        # Encode the dictionary back into a string
        param_str = str(param_dict)
        param_str = param_str.replace("\\", "\\\\")
        return param_str
    except Exception as e:
        print(f"Error when encoding dictionary to Python program: {e}")
        sys.exit(1)

def _replace_parameters_in_code(code_snippet, new_param_str):
    try:
        # Use regex to replace the old dictionary part with the new one
        pattern = re.compile(r"(processing.run\([^,]+, ){[^}]+}(.*\))")
        new_code = pattern.sub(rf"\1{new_param_str}\2", code_snippet)
        return new_code
    except Exception as e:
        print(f"Error when replacing generated code to Python program: {e}")
        sys.exit(1)

def decode_qgis_python(program_path):
    decoded_params = {}
    with open(program_path, "r") as f:
        code_snippet = f.read()
        param_str = _extract_parameters_from_code(code_snippet)
        decoded_params = _decode_parameters(param_str)
    return decoded_params

def generate_qgis_python(program_path, decoded_params, output_dir_path):
    new_command_string = _encode_parameters(decoded_params)
    with open(program_path, "r") as f:
        original_code_snippet = f.read()
        replaced_snippet = _replace_parameters_in_code(original_code_snippet, new_command_string)
        program_path = os.path.join(output_dir_path, "program.py")
        with open(program_path, "w") as f:
            f.write(replaced_snippet)
    return program_path

def check_requirement(command_type="qgis-command"):
    pass

def get_software_config(command_type="qgis-command"):
    software_config = {}
    if command_type.startswith("qgis"):
        try:
            # Get QGIS installed directory
            qgis_basedir_path = get_qgis_directory()
            # Get executable path of qgis_process
            qgis_process_path = get_qgis_process_path(qgis_basedir_path)
            # Try to run 'qgis_process' with the '--help' flag
            qgis_version = subprocess.run([qgis_process_path, '--version'], capture_output=True, text=True)
            if qgis_version.returncode == 0:
                print(f"- Found qgis_process path in {qgis_process_path}")
                qgis_plugins = _parse_qgis_plugins(qgis_version.stdout)
                software_config["plugins"] = qgis_plugins
            if command_type == "qgis-command":
                software_config["exec_path"] = qgis_process_path
                return software_config
            elif command_type == "qgis-python":
                try:
                    # Get executable path of qgis_process
                    qgis_python_path = get_qgis_python_path(qgis_basedir_path)
                    print(f"- Found qgis python path in {qgis_python_path}")
                    # Try to run 'qgis_process' with the '--help' flag
                    result = subprocess.run([qgis_python_path, '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if result.returncode == 0:
                        print("The QGIS python command exists.")
                    software_config["exec_path"] = qgis_python_path
                    return software_config
                except FileNotFoundError:
                    print("The QGIS python command not found. Please ensure QGIS is installed.n \
                        - For Windows: setx QGIS_PATH=path_to_your_QGIS_installation\n \
                        - For Linux/MacOS: export QGIS_PATH=path_to_your_QGIS_installation")
                    sys.exit(1)
                except subprocess.CalledProcessError:
                    print("The QGIS python command exists but returned an error.")
                    sys.exit(1)
            else:
                print("Invalid process type. The program only support following type [qgis-command, qgis-python]")
                sys.exit(1)
        except FileNotFoundError:
            print("qgis_process command not found. Please ensure QGIS is installed.n \
                   - For Windows: setx QGIS_PATH=path_to_your_QGIS_installation\n \
                   - For Linux/MacOS: export QGIS_PATH=path_to_your_QGIS_installation")
            sys.exit(1)
        except subprocess.CalledProcessError:
            print("qgis_process command exists but returned an error.")
            sys.exit(1)

def _parse_qgis_plugins(version):
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

def execute_command(command, params=[]):
    results = {"finished": False}
    monitor_thread = threading.Thread(target=monitor_usage, args=(results,))
    monitor_thread.start()
    
    exec_start_time = time.time()
    try:
        command = [command] + params
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

def get_qgis_process_path(qgis_basedir_path):
    # QGIS binary directory
    qgis_bin_dir = ""
    # Provide default directory based on the operating system
    os_type = platform.system()
    if os_type == 'Windows':
        qgis_bin_dir =  os.path.join(qgis_basedir_path, "bin")
    elif os_type == 'Linux':
        qgis_bin_dir = qgis_basedir_path
    elif os_type == 'Darwin':  # macOS
        qgis_bin_dir = os.path.join(qgis_basedir_path, "bin")
    else:
        raise OSError('Unsupported operating system')
    path_result = find_file_prefix(qgis_bin_dir, "qgis_process")
    if path_result is None:
        print("QGIS process path not found")
        sys.exit(1)
    return path_result

def get_qgis_python_path(qgis_basedir_path):
    # QGIS binary directory
    qgis_bin_dir = ""
    # Provide default directory based on the operating system
    os_type = platform.system()
    if os_type == 'Windows':
        qgis_apps_dir = os.path.join(qgis_basedir_path, "apps")
        qgis_python_dir = find_dir_prefix(qgis_apps_dir, "Python")
        if qgis_python_dir is None:
            return None
        qgis_bin_dir =  os.path.join(qgis_python_dir)
    elif os_type == 'Linux':
        qgis_bin_dir = f'{qgis_basedir_path}'
    elif os_type == 'Darwin':  # macOS
        qgis_bin_dir = os.path.join(qgis_basedir_path, "bin")
    else:
        raise OSError('Unsupported operating system')
    path_result = find_file_prefix(qgis_bin_dir, "python3")
    if path_result is None:
        print("QGIS Python path not found")
        sys.exit(1)
    return path_result

def find_file_prefix(directory, prefix):
    executable_extensions = ['.exe', '.bat', '.cmd', '.com', '.ps1']
    # Check if the directory exists
    if not os.path.isdir(directory):
        print(f"The directory {directory} does not exist.")
        return None
    # List all files in the directory
    for file_name in os.listdir(directory):
        # Check if the file name starts with the given prefix and is an executable
        if file_name.startswith(prefix):
            if platform.system() == 'Windows':
                if file_name.lower().endswith(tuple(executable_extensions)):
                    return os.path.join(directory, file_name)
            else:
                return os.path.join(directory, file_name)
    return None

def find_dir_prefix(directory, prefix):
    executable_extensions = ['.exe', '.bat', '.cmd', '.com', '.ps1']
    # Check if the directory exists
    if not os.path.isdir(directory):
        print(f"The directory {directory} does not exist.")
        return None
    # List all files in the directory
    for file_name in os.listdir(directory):
        # Check if the file name starts with the given prefix and is an executable
        if file_name.startswith(prefix):
            return os.path.join(directory, file_name)
    return None

def get_qgis_directory():
    # Check if QGIS_PATH environment variable exists
    qgis_path = os.getenv('QGIS_PATH')
    if qgis_path:
        return qgis_path
    
    # Provide default directory based on the operating system
    os_type = platform.system()
    if os_type == 'Windows':
        return r'C:\Program Files\QGIS'
    elif os_type == 'Linux':
        return '/usr/bin'
    elif os_type == 'Darwin':  # macOS
        return '/Applications/QGIS.app/Contents/MacOS'
    else:
        raise OSError('Unsupported operating system')
