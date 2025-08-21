import importlib.resources as pkg_resources
import os
import platform
import psutil
import shutil
import subprocess
import time

from jinja2 import Environment, FileSystemLoader, exceptions as jinja_exceptions

from .process_monitor import ProcessMonitor


class CommandType:
    def __init__(self, scenario):
        self.scenario = scenario

    def execute_command(self, command_list, params: list=None):
        if not params:
            params = []

        results = {"finished": False}

        workdir = self.scenario.workdir

        # Start execution
        exec_start_time = time.time()
        process = None # Ensure process is defined
        command_to_execute = command_list + params # Define here for use in except block
        try:
            # Start process
            process = psutil.Popen(command_to_execute, shell=False, cwd=workdir)
            results["pid"] = process.pid # Store PID early

            # Run monitoring function (this blocks until the process and its children complete)
            pm = ProcessMonitor()
            pm.run_monitoring(process)

            # Get collected metrics from ProcessMonitor
            collected_metrics = pm.get_metrics()
            results.update(collected_metrics)

            # process.returncode should be set as start_monitoring waits for completion
            results["success"] = (process.returncode == 0)
            if not results["success"]:
                print(f"Command '{' '.join(command_to_execute)}' failed with exit code {process.returncode}")

        except FileNotFoundError: # Specific to executable not found
            results["success"] = False
            print(f"Command executable not found for: {' '.join(command_to_execute)}")
            raise FileNotFoundError(f"Executable not found for command: {' '.join(command_to_execute)}.")

        except psutil.Error as e: # Catch other psutil errors during Popen or process interaction
            results["success"] = False
            print(f"psutil error during command execution '{' '.join(command_to_execute)}': {e}")
            pid_info = f" (PID: {process.pid})" if process and hasattr(process, 'pid') else ""
            raise RuntimeError(f"psutil error executing command '{' '.join(command_to_execute)}'{pid_info}: {e}")

        except Exception as e: # Catch any other unexpected errors
            results["success"] = False
            print(f"Unexpected error during command execution '{' '.join(command_to_execute)}': {e}")
            pid_info = f" (PID: {process.pid})" if process and hasattr(process, 'pid') else ""
            raise RuntimeError(f"Unexpected error executing command '{' '.join(command_to_execute)}'{pid_info}: {e}")

        results["finished"] = True
        exec_end_time = time.time()
        results["start_time"] = exec_start_time
        results["end_time"] =  exec_end_time

        return results


    def get_software_config(self):
        raise NotImplementedError("Subclasses must implement get_software_config method")


    def get_exec_params(self, command, params_dict, output_dir_path):
        raise NotImplementedError("Subclasses must implement get_exec_params method")


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
                    full_path = os.path.join(directory, file_name)
                    # For non-Windows, check if it's executable
                    if os.access(full_path, os.X_OK):
                        return full_path
                    # If not executable, continue search (or could log a warning)
        return None


    def _get_qgis_process_path(self, qgis_basedir_path):
        qgis_bin_dir = None

        os_type = platform.system()

        if os_type == 'Windows':
            qgis_bin_dir =  os.path.join(qgis_basedir_path, "bin")

        elif os_type == 'Linux':
            qgis_bin_dir = qgis_basedir_path

        elif os_type == 'Darwin':
            qgis_bin_dir = os.path.join(qgis_basedir_path, "bin")

        else:
            raise OSError('Unsupported operating system')

        path_result = self._find_file_prefix(qgis_bin_dir, "qgis_process")

        if path_result is None:
            raise FileNotFoundError(f"QGIS 'qgis_process' executable not found in derived path '{qgis_bin_dir}'.")

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

        qgis_basedir_path = self._get_qgis_directory()
        qgis_process_path = self._get_qgis_process_path(qgis_basedir_path)

        try:
            qgis_version_result = subprocess.run([qgis_process_path, '--version'], capture_output=True, text=True, check=False)

            if qgis_version_result.returncode != 0:
                error_msg = f"QGIS 'qgis_process --version' command failed with exit code {qgis_version_result.returncode} using '{qgis_process_path}'."
                if qgis_version_result.stderr:
                    error_msg += f" Stderr: {qgis_version_result.stderr.strip()}"
                print(error_msg)
                raise RuntimeError(error_msg)

            print(f"- Found qgis_process path in {qgis_process_path}")
            qgis_plugins = self._parse_qgis_plugins(qgis_version_result.stdout)
            software_config["plugins"] = qgis_plugins
            software_config["exec_path"] = [qgis_process_path]

        except FileNotFoundError as err:
            msg = f"QGIS 'qgis_process' executable found at '{qgis_process_path if 'qgis_process_path' in locals() else 'unknown path'}' but subprocess.run failed to execute it (FileNotFoundError)."
            print(msg)
            raise FileNotFoundError(msg) from err

        except subprocess.SubprocessError as err:
            msg = f"Error running 'qgis_process --version': {e}"
            print(msg)
            raise RuntimeError(msg) from err

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
        qgis_bin_dir = None
        os_type = platform.system()

        if os_type == 'Windows':
            qgis_apps_dir = os.path.join(qgis_basedir_path, "apps")
            qgis_python_dir = self._find_dir_prefix(qgis_apps_dir, "Python")
            if qgis_python_dir is None:
                return None
            qgis_bin_dir =  os.path.join(qgis_python_dir)

        elif os_type == 'Linux':
            qgis_bin_dir = f'{qgis_basedir_path}'

        elif os_type == 'Darwin':
            qgis_bin_dir = os.path.join(qgis_basedir_path, "bin")

        else:
            raise OSError(f"Unsupported operating system '{os_type}'.")

        path_result = self._find_file_prefix(qgis_bin_dir, "python3")
        if not path_result:
            raise FileNotFoundError(f"QGIS Python executable not found in derived path '{qgis_bin_dir}'.")

        return path_result


    def get_software_config(self):
        software_config = {}

        qgis_basedir_path = super()._get_qgis_directory()
        qgis_python_path = self._get_qgis_python_path(qgis_basedir_path)

        try:

            print(f"- Found QGIS python path in {qgis_python_path}")
            result = subprocess.run([qgis_python_path, '--version'], capture_output=True, text=True, check=False)

            if result.returncode != 0:
                error_msg = f"QGIS Python '--version' command failed with exit code {result.returncode} using '{qgis_python_path}'."
                if result.stderr:
                    error_msg += f" Stderr: {result.stderr.strip()}"
                print(error_msg)
                raise RuntimeError(error_msg)

            software_config["exec_path"] = [qgis_python_path]

        except FileNotFoundError as err:
            msg = f"QGIS Python executable found at '{qgis_python_path if 'qgis_python_path' in locals() else 'unknown path'}' but subprocess.run failed to execute it (FileNotFoundError)."
            print(msg)
            raise FileNotFoundError(msg) from err

        except subprocess.SubprocessError as err:
            msg = "Error running QGIS Python '--version'."
            print(msg)
            raise RuntimeError(msg) from err

        return software_config


    def _render_template(self, template_name, **kwargs):
        try:
            with pkg_resources.path(__package__, 'templates') as template_dir:
                env = Environment(loader=FileSystemLoader(template_dir))
                template = env.get_template(template_name)
                return template.render(**kwargs)

        except jinja_exceptions.TemplateNotFound:
            raise FileNotFoundError(f"Jinja2 template '{template_name}' not found in templates.")

        except Exception as e: # Catch other potential errors during template rendering
            raise RuntimeError(f"Error rendering template '{template_name}': {e}")


    def _encode_parameters(self, param_dict):
        try:
            if not param_dict: # Handles empty dict or None
                return ""
            # Encode the dictionary back into a string
            param_str = str(param_dict)
            # Basic escaping for backslashes, consider more robust serialization if needed
            param_str = param_str.replace("\\", "\\\\")
            return param_str

        except Exception as err:
            raise ValueError(f"Cannot encode parameter to string for QGISPython.") from err


    def get_exec_params(self, command, params_dict, output_dir_path):
        params_str = self._encode_parameters(params_dict)
        script_line_str = f'processing.run("{command}", {params_str})'
        rendered_code = self._render_template('program.j2', script_line=script_line_str)

        program_path = os.path.join(output_dir_path, "program.py")
        with open(program_path, "w") as f:
            f.write(rendered_code)

        return [program_path]


class Python(CommandType):
    def get_software_config(self):
        software_config = {}
        os_type = platform.system()
        python_executable = None

        venv = self.scenario.venv

        if venv is not None:
            if not os.path.isdir(venv):
                raise FileNotFoundError(f"Virtual environment directory not found at '{venv}'.")

            # Common Python executable names in venvs
            potential_execs = ["python", "python3"]
            if os_type == "Windows":
                potential_execs = ["python.exe", "python3.exe"]

            found_in_venv = False
            for exec_name in potential_execs:
                current_path = os.path.join(venv, "Scripts" if os_type == "Windows" else "bin", exec_name)
                if os.path.isfile(current_path) or os.path.islink(current_path):
                    python_executable = current_path
                    found_in_venv = True
                    break
            if not found_in_venv:
                raise FileNotFoundError(f"Python executable not found in venv '{venv}'.")

        else:
            found_path = shutil.which("python")
            if found_path is None:
                found_path = shutil.which("python3")
                if found_path is None:
                    raise FileNotFoundError("System Python executable not found in PATH.")
            python_executable = found_path

        software_config["exec_path"] = [python_executable]
        return software_config


    def get_exec_params(self, script_path, decoded_params, output_dir_path):
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Python script not found at '{script_path}'.")

        try:
            output_file_name = os.path.basename(script_path)
            output_file_path = os.path.join(output_dir_path, output_file_name)
            shutil.copyfile(script_path, output_file_path)

        except IOError as err:
            raise IOError(f"Failed to copy Python script from '{script_path}' to '{output_dir_path}'.") from err

        # The script path for execution should be the one in output_dir_path
        command_with_params = self._encode_parameters(output_file_path, decoded_params)
        return command_with_params


    def _encode_parameters(self, script_path, params):
        try:
            # Initialize the param_list with the script path (which is now the path in output_dir)
            param_list = [script_path]

            if isinstance(params, dict):
                for key, value in params.items():
                    param_list.append(f"--{key}={value}")
            elif isinstance(params, list):
                # Ensure all list parameters are converted to strings
                param_list.extend(str(p) for p in params)
            return param_list

        except Exception as err:
            raise ValueError(f"Cannot encode Python script parameters.") from err


class Shell(CommandType):
    def get_software_config(self):
        splitted_command = self.scenario.command.split(" ")
        script_path = splitted_command[0]

        software_config = {
            "exec_path": [script_path]
        }
        return software_config


    def get_exec_params(self, command, decoded_params, output_dir_path):
        splitted_command = command.split(" ")
        script_path = splitted_command[0]
        command_params = []

        if len(splitted_command) > 1:
            splited_command_params = splitted_command[1:]
            for p in splited_command_params:
                    if not isinstance(p, str):
                        p = str(p)
                    command_params.append(p)

        # script_path is splitted_command[0]. This could be 'bash' or an actual script path.
        # command_params are splitted_command[1:]

        # If script_path appears to be a file, it must exist and be copied.
        # Otherwise, script_path is treated as the main executable (e.g., 'bash', 'sh').
        is_executable_file_scenario = os.path.isfile(script_path)
        executable_to_run = script_path

        if is_executable_file_scenario:
            try:
                output_file_name = os.path.basename(script_path)
                output_file_path = os.path.join(output_dir_path, output_file_name)
                shutil.copyfile(script_path, output_file_path)
                executable_to_run = output_file_path # Run the copied script

            except FileNotFoundError as err:
                raise FileNotFoundError(f"Shell script not found at '{script_path}'.") from err

            except IOError as err:
                raise IOError(f"Failed to copy shell script from '{script_path}' to '{output_dir_path}'.") from err

        else:
            # If script_path is not a file (e.g. 'bash'), check if it's in PATH
            if shutil.which(script_path) is None:
                raise FileNotFoundError(f"Shell command '{script_path}' not found in PATH and is not a local file.")

        # Construct the full command list
        # The first element is the executable (either copied script or command like 'bash')
        # Then, arguments from the original command string (command_params)
        # Finally, additional parameters from decoded_params
        final_command_list = [executable_to_run]
        final_command_list.extend(command_params) # These are args that were part of the original command string

        # _encode_parameters for Shell should only process decoded_params
        additional_encoded_params = self._encode_parameters(None, decoded_params) # Pass None for script_path placeholder
        final_command_list.extend(additional_encoded_params)

        return final_command_list


    def _encode_parameters(self, _, params):
        # script_path (first arg) is ignored for Shell as it's handled in get_exec_params
        try:
            param_list = []
            if isinstance(params, dict):
                for key, value in params.items():
                    param_list.append(f"--{key}={value}")
            elif isinstance(params, list):
                # Ensure all list parameters are converted to strings
                for p in params:
                    param_list.append(str(p))
            return param_list

        except Exception as err:
            raise ValueError(f"Cannot encode shell parameters.") from err


class CommandFactory:
    @staticmethod
    def create_command(scenario):
        if scenario.type == "qgis-process":
            return QGISProcess(scenario)
        elif scenario.type == "qgis-python":
            return QGISPython(scenario)
        elif scenario.type.startswith("python"):
            return Python(scenario)
        elif scenario.type.startswith("shell"):
            return Shell(scenario)
        else:
            raise ValueError(f"Invalid scenario type '{scenario.type}'.")


def get_instance(scenario):
    instance = CommandFactory.create_command(scenario)
    return instance