import json
import os
import time
import pandas as pd
from datetime import datetime
# import ansible_runner

from .scenario import Scenario
from . import recording
from . import command

CSV_FILE = 'benchmark_results.csv'

class Benchmark:

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.result = {
            "name": scenario.name
        }
    
    def _makedirs_if_not_exists(self, dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def _create_directories_for_scenarios(self, base_output, name, scenario_combination, repeat):
        base_dir  =  os.path.join(base_output, name)
        self._makedirs_if_not_exists(base_dir)

        for idx, scenario in enumerate(scenario_combination):
            base_dir = os.path.join(base_dir, f"set_{idx + 1}")
            self._makedirs_if_not_exists(base_dir)
            
            for i in range(1, repeat + 1):
                repeat_dir = os.path.join(base_dir, f"run_{i}")
                self._makedirs_if_not_exists(repeat_dir)

    def _save_result(self):
        output_file  =  os.path.join(self.scenario.temp_directory, self.scenario.name, "output.json")
        with open(output_file, 'w') as json_file:
            json.dump(self.result, json_file, indent=4)

    # Run the benchmark according to methodology
    def run(self):
        # Get or create base directory based on the temporary directory and testing scenario name
        base_dir  =  os.path.join(self.scenario.temp_directory, self.scenario.name)
        self._makedirs_if_not_exists(base_dir)

        # Record system configuration. Store recorded data on the file.
        print("Recording system configuration\n")
        system_info = recording.get_system_info()
        self.result["system"] = system_info
        self._save_result()

        # Record process info for specific duration in seconds (e.x. 15s). Default value is 10s.
        recording_duration = 10
        # Read recording duration value from environment
        recording_duration_env = os.getenv('GB_RECORD_DURATION')
        if recording_duration_env:
            # Try to convert to integer
            try :
                recording_duration = float(recording_duration_env)
            except (ValueError, TypeError):
                # Use default value
                pass
        print(f"Check running process for {recording_duration} seconds\n")
        running_process = recording.record_process_info(duration=recording_duration)
        # self.result["process"] = running_process
        # self._save_result()

        # Check the availability of the tools and libraries for running benchmark
        print(f"Check system requirement\n")
        command.check_requirement(command_type=self.scenario.type)
        
        # To do: Decide if the system is suitable for testing

        # Baseline monitoring for specific duration in seconds (e.x. 15 sec). Store recorded data on the file.
        print(f"Baseline monitoring for {recording_duration} seconds\n")
        baseline_results = recording.monitor_baseline(duration=recording_duration)
        self.result["baseline"] = baseline_results
        self._save_result()

        # Record software configuration
        print("Recording software configuration")
        software_config = command.get_software_config(self.scenario.type)
        exec_path = software_config["exec_path"]
        self.result["software"] = software_config
        print()

        # Measure start time of the whole tests
        start_time = time.time()
        start_time_hr = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')

        decoded_params = {}
        if(self.scenario.type == "qgis-command"):
            # Decode user defined command string in yaml scenario file
            decoded_params = command.decode_qgis_command(self.scenario.command)
        elif(self.scenario.type == "qgis-python"):
            # Decode user defined command string in yaml scenario file
            decoded_params = command.decode_qgis_python(self.scenario.command_file)

        # Store results
        result_list = []

        print("Generating test scenario\n")
        # Generate test for any input combination
        for idx_input, input in enumerate(self.scenario.inputs):
            abs_path = os.path.abspath(input)
            decoded_params["INPUT"] = abs_path
            # Generate test for any combination of parameters
            for idx, params in enumerate(self.scenario.combination):
                # Get or create scenario directory
                scen_dir = os.path.join(base_dir, f"set_{idx + 1}")
                self._makedirs_if_not_exists(scen_dir)

                # Update the command parameter
                for key_param, value_param in params.items():
                    decoded_params[key_param] = value_param

                # Generate for each repeatable test run
                for i in range(1, self.scenario.repeat + 1):
                    # Get or create test run directory
                    repeat_dir = os.path.join(scen_dir, f"run_{i}")
                    self._makedirs_if_not_exists(repeat_dir)
                    # Record the running process before test run
                    print(f"Recording running process for {recording_duration} seconds\n")
                    running_process = recording.record_process_info(duration=recording_duration)
                    # Define the path of the execution output
                    output_file_path = os.path.abspath(os.path.join(repeat_dir, f"{idx_input}_{self.scenario.outputs['OUTPUT']}"))
                    decoded_params["OUTPUT"] = output_file_path
                    if(self.scenario.type == "qgis-command"):
                        # Encode the command to string
                        command_params = command.encode_qgis_command(decoded_params)
                        command_params = command_params.split()
                        # command_string = fr"{exec_path} {command_string}"
                    elif(self.scenario.type == "qgis-python"):
                        command_params = command.generate_qgis_python(self.scenario.command_file, decoded_params, repeat_dir)
                        command_params = [command_params]
                        # command_string = fr"{exec_path} {program_path}"
                    
                    # Print for debugging
                    print()
                    print(f"Running scenario with params {params} for repetition {i}. Output saved on {repeat_dir}")
                    print(f"{exec_path} {command_params}")
                    print()
                    # Execute the command
                    exec_result = command.execute_command(exec_path, command_params)
                    # Individual result
                    result = {
                        "parameters": decoded_params,
                        "repeat": i,
                        "success": exec_result["success"],
                        "start_time": exec_result["start_time"],
                        "end_time": exec_result["end_time"],
                        "exec_time": exec_result["end_time"] - exec_result["start_time"],
                        "avg_cpu": exec_result["avg_cpu"],
                        "avg_mem": exec_result["avg_mem"],
                        "process": running_process
                    }
                    # Append result to the list
                    result_list.append(result)
                    # Store the temporary result to json output file
                    self.result["results"] = result_list
                    self._save_result()

        # Measure end time of a whole tests
        end_time = time.time()
        end_time_hr = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')

        # Calculate execution time
        execution_time = end_time - start_time

        # Store results in CSV
        record = {
            'test_name': self.scenario.name,
            'start_time': start_time,
            'end_time': end_time,
            'start_time_hr': start_time_hr,
            'end_time_hr': end_time_hr,
            'execution_time': execution_time
        }
        
        df = pd.DataFrame([record])
        
        try:
            existing_df = pd.read_csv(CSV_FILE)
            existing_df = existing_df[existing_df['test_name'] != self.scenario.name]  # Remove existing entry if any
            df = pd.concat([existing_df, df], ignore_index=True)
        except FileNotFoundError:
            pass  # If file doesn't exist, we will create a new one
        
        df.to_csv(CSV_FILE, index=False)
        print(f'Test finished. Result for "{self.scenario.name}" saved.')

class Results:
    @classmethod
    def delete_test_result(cls, test_name):
        try:
            df = pd.read_csv(cls.CSV_FILE)
            df = df[df['test_name'] != test_name]
            df.to_csv(cls.CSV_FILE, index=False)
            print(f'Test result for "{test_name}" deleted.')
        except FileNotFoundError:
            print(f'No results found to delete for "{test_name}".')

    @classmethod
    def list_all_results(cls):
        try:
            df = pd.read_csv(cls.CSV_FILE)
            print(df)
        except FileNotFoundError:
            print('No results found.')
    
    @classmethod
    def get_test_instance(cls, test_name):
        try:
            df = pd.read_csv(cls.CSV_FILE)
            record = df[df['test_name'] == test_name].to_dict('records')
            if record:
                instance = {}
                instance["test_name"] = test_name
                instance["start_time"] = record[0]['start_time'] 
                instance["end_time"] = record[0]['end_time']
                instance["start_time_hr"] = record[0]['start_time_hr'] 
                instance["end_time_hr"] = record[0]['end_time_hr']
                instance["execution_time"] = record[0]['execution_time']
                return instance
            else:
                print(f'No test found with the name "{test_name}".')
                return None
        except FileNotFoundError:
            print('No results found.')
            return None

# Example usage:
# benchmark = Benchmark('test1', './test_script.sh')
# benchmark.run()
# Benchmark.delete_test_result('test1')