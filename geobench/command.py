import shutil
import sys

import subprocess
import time
import os
import platform
import importlib.resources as pkg_resources
from jinja2 import Environment, FileSystemLoader
import psutil

from . import error
from .recording import monitor_usage
from .process_monitor import ProcessMonitor

def execute_command(command_list, params=[]):
    results = {"finished": False}
    
    # Start execution
    exec_start_time = time.time()
    try:
        command = command_list + params
        # Start process immeaditely (NON-BLOCKING)
        process = psutil.Popen(command, shell=False)
        # Run monitoring function
        # monitor_usage(results, process)
        pm = ProcessMonitor()
        pm.start_monitoring(process)
        # Get collected metrics
        collected_metrics = pm.get_metrics()
        # Update results with collected metrics
        results.update(collected_metrics)
        # Set success flag to True if the process completed without raising an exception
        results["success"] = True
    except subprocess.CalledProcessError as e:
        results["success"] = False
        print(f"Command failed with {e.returncode}")
    # Store process id
    results["pid"] = process.pid
    results["finished"] = True
    exec_end_time = time.time()
    results["start_time"] = exec_start_time
    results["end_time"] =  exec_end_time

    return results

class CommandType:
    def get_software_config(self):
        raise NotImplementedError("Subclasses must implement get_software_config method")
    def get_exec_params(self, command, params_dict, output_dir_path):
        raise NotImplementedError("Subclasses must implement get_exec_params method")
    def check_requirement(self):
        pass

class QGISProcess(CommandType):
    def _get_qgis_directory(self):
        # Check if QGIS_PATH environment variable exists
        qgis_path = os.getenv('QGIS_PATH')
        if qgis_path:
            return qgis_path
        
        # Provide default directory based on the operating system
        os_type = platform.system()
        if os_type == 'Windows':
            return r'C:\\Program Files\\QGIS'
        elif os_type == 'Linux':
            return '/usr/bin'
        elif os_type == 'Darwin':  # macOS
            return '/Applications/QGIS.app/Contents/MacOS'
        else:
            raise OSError('Unsupported operating system')
    
    def _find_file_prefix(self, directory, prefix):
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
    
    def _get_qgis_process_path(self, qgis_basedir_path):
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
        path_result = self._find_file_prefix(qgis_bin_dir, "qgis_process")
        if path_result is None:
            raise FileNotFoundError("QGIS process path not found")
        return path_result
    
    def _parse_qgis_plugins(self, version):
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

    def get_software_config(self):
        software_config = {}
        try:
            qgis_basedir_path = self._get_qgis_directory()
            qgis_process_path = self._get_qgis_process_path(qgis_basedir_path)
            qgis_version = subprocess.run([qgis_process_path, '--version'], capture_output=True, text=True)
            if qgis_version.returncode == 0:
                print(f"- Found qgis_process path in {qgis_process_path}")
                qgis_plugins = self._parse_qgis_plugins(qgis_version.stdout)
                software_config["plugins"] = qgis_plugins
            software_config["exec_path"] = [qgis_process_path]
        except FileNotFoundError as e:
            print("qgis_process command not found. Please ensure QGIS is installed.")
            print(f"Specific error message: {e}")
            sys.exit(1)
        except subprocess.CalledProcessError:
            print("qgis_process command exists but returned an error.")
            sys.exit(1)
        return software_config
    
    def get_exec_params(self, command, params_dict, output_dir_path):
        params = ["run", command]
        for key, value in params_dict.items():
            params.append(f"--{key}={value}")
        return params

class QGISPython(QGISProcess):
    def _find_dir_prefix(self, directory, prefix):
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
    
    def _get_qgis_python_path(self, qgis_basedir_path):
        # QGIS binary directory
        qgis_bin_dir = ""
        # Provide default directory based on the operating system
        os_type = platform.system()
        if os_type == 'Windows':
            qgis_apps_dir = os.path.join(qgis_basedir_path, "apps")
            qgis_python_dir = self._find_dir_prefix(qgis_apps_dir, "Python")
            if qgis_python_dir is None:
                return None
            qgis_bin_dir =  os.path.join(qgis_python_dir)
        elif os_type == 'Linux':
            qgis_bin_dir = f'{qgis_basedir_path}'
        elif os_type == 'Darwin':  # macOS
            qgis_bin_dir = os.path.join(qgis_basedir_path, "bin")
        else:
            raise OSError('Unsupported operating system')
        path_result = self._find_file_prefix(qgis_bin_dir, "python3")
        if path_result is None:
            raise FileNotFoundError("QGIS Python path not found")
        return path_result
    
    def get_software_config(self):
        software_config = {}
        try:
            qgis_basedir_path = super()._get_qgis_directory()
            qgis_python_path = self._get_qgis_python_path(qgis_basedir_path)
            print(f"- Found qgis python path in {qgis_python_path}")
            result = subprocess.run([qgis_python_path, '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            software_config["exec_path"] = [qgis_python_path]
        except FileNotFoundError:
            print("The QGIS python command not found. Please ensure QGIS is installed.")
            sys.exit(1)
        except subprocess.CalledProcessError:
            print("The QGIS python command exists but returned an error.")
            sys.exit(1)
        return software_config
    
    def _render_template(self, template_name, **kwargs):
        with pkg_resources.path(__package__, 'templates') as template_dir:
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template(template_name)
            return template.render(**kwargs)
    
    def _encode_parameters(self, param_dict):
        try:
            if param_dict == {}:
                return ""
            # Encode the dictionary back into a string
            param_str = str(param_dict)
            param_str = param_str.replace("\\", "\\\\")
            return param_str
        except Exception as e:
            raise Exception(f"Error when encoding dictionary to Python program: {e}")
    
    def get_exec_params(self, command, params_dict, output_dir_path):
        params_str = self._encode_parameters(params_dict)
        script_line_str = f'processing.run("{command}", {params_str})'
        rendered_code = self._render_template('program.j2', script_line=script_line_str)

        program_path = os.path.join(output_dir_path, "program.py")
        with open(program_path, "w") as f:
            f.write(rendered_code)
        
        return [program_path]

class Python(CommandType):
    def __init__(self, venv=None):
        self.venv = venv

    def get_software_config(self):
        software_config = {}
        os_type = platform.system()
        python_executable = "python3"

        if self.venv is not None:
            if os.path.isdir(self.venv):
                if os_type == "Windows":
                    python_executable = os.path.join(self.venv, "Scripts", "python3.exe")
                else:
                    python_executable = os.path.join(self.venv, "bin", "python3")
                
                if not os.path.isfile(python_executable):
                    raise FileNotFoundError(f"Python executable not found at: {python_executable}")
            else:
                raise FileNotFoundError(f"Virtual environment not found at: {self.venv}")

        software_config["exec_path"] = [python_executable]
        return software_config

    def get_exec_params(self, script_path, decoded_params, output_dir_path):
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Python script not found at: {script_path}")
        
        output_file_path = os.path.join(output_dir_path, os.path.basename(script_path))
        shutil.copyfile(script_path, output_file_path)
        
        command_with_params = self._encode_parameters(script_path, decoded_params)
        return command_with_params

    def _encode_parameters(self, script_path, params):
        try:
            # Initialize the param_list with the script path
            param_list = [script_path]
            
            # Check if the params are a dictionary
            if isinstance(params, dict):
                for key, value in params.items():
                    # Append string values with quotes to a list
                    param_list.append(f"--{key}={value}")
            elif isinstance(params, list):
                # If params is a list, extend the param_list with the list
                param_list.extend(params)
            # Return script path and parameters as a list
            return param_list
        except Exception as e:
            raise Exception(f"Error when encoding input parameters: {e}")

class Shell(CommandType):

    def get_exec_params(self, script_path, decoded_params, output_dir_path):
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Shell script not found at: {script_path}")
        
        output_file_path = os.path.join(output_dir_path, os.path.basename(script_path))
        shutil.copyfile(script_path, output_file_path)
        
        command_with_params = self._encode_parameters(script_path, decoded_params)
        return command_with_params

    def _encode_parameters(self, script_path, params):
        try:
            # Initialize the param_list with the script path
            param_list = [script_path]
            
            # Check if the params are a dictionary
            if isinstance(params, dict):
                for key, value in params.items():
                    # Append string values with quotes to a list
                    param_list.append(f"--{key}={value}")
            elif isinstance(params, list):
                # If params is a list, extend the param_list with the list
                param_list.extend(params)
            # Return script path and parameters as a list
            return param_list
        except Exception as e:
            raise Exception(f"Error when encoding input parameters: {e}")

class CommandFactory:
    @staticmethod
    def create_command(scenario):
        if scenario.type == "qgis-process":
            return QGISProcess()
        elif scenario.type == "qgis-python":
            return QGISPython()
        elif scenario.type.startswith("python"):
            return Python(scenario.venv)
        elif scenario.type.startswith("shell"):
            return Shell()
        else:
            raise ValueError("Invalid process type. The program only supports [qgis-process, qgis-python, python, shell]")

def get_instance(scenario):
    instance = CommandFactory.create_command(scenario)
    return instance