import json
import os
import shutil
import time
import pandas as pd
from datetime import datetime

import importlib.resources as pkg_resources

from .scenario import Scenario
from . import system_recording as recording
from . import command

CSV_FILE = 'benchmark_results.csv'
OUTPUT_JSON_FILENAME = "output.json"
INDEX_HTML_FILENAME = "index.html"
RESULT_HTML_FILENAME = "result.html"
RUN_RESULT_JSON_FILENAME = "result.json"
RUN_PROCESS_JSON_FILENAME = "process.json"

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
        output_file  =  os.path.join(self.scenario.temp_directory, self.scenario.name, OUTPUT_JSON_FILENAME)
        with open(output_file, 'w') as json_file:
            json.dump(self.result, json_file, indent=4)

    def _setup_environment(self, base_dir):
        """Creates base directories and copies template files."""
        self._makedirs_if_not_exists(base_dir)
        with pkg_resources.path(__package__, 'templates') as template_dir:
            shutil.copy(os.path.join(template_dir, INDEX_HTML_FILENAME), base_dir)
            shutil.copy(os.path.join(template_dir, RESULT_HTML_FILENAME), base_dir)

    def _record_initial_system_info(self):
        """Records system hardware information."""
        print("Recording system configuration\n")
        system_info = recording.get_system_info()
        self.result["system"] = system_info
        self._save_result()

    def _get_recording_duration(self):
        """Gets the recording duration from environment or uses default."""
        recording_duration = 10  # Default value
        recording_duration_env = os.getenv('GB_RECORD_DURATION')
        if recording_duration_env:
            try:
                recording_duration = float(recording_duration_env)
            except (ValueError, TypeError):
                pass  # Use default value if conversion fails
        return recording_duration

    def _perform_pre_run_diagnostics(self, instance, recording_duration):
        """Performs pre-run checks, monitoring, and records software config."""
        print(f"Check running process for {recording_duration} seconds\n")
        # Initial running process check (original code recorded this but didn't store in self.result immediately)
        # recording.record_process_info(duration=recording_duration)
        # self.result["process"] = running_process # This was commented out in original
        # self._save_result()

        print(f"Check system requirement\n")
        instance.check_requirement()
        # To do: Decide if the system is suitable for testing

        print(f"Baseline monitoring for {recording_duration} seconds\n")
        baseline_results = recording.monitor_baseline(duration=recording_duration)
        self.result["baseline"] = baseline_results
        self._save_result()

        print("Recording software configuration")
        software_config = instance.get_software_config()
        self.result["software"] = software_config
        self._save_result() # Save after software config
        print()
        return software_config.get("exec_path")

    def _execute_single_test_run(self, base_dir, scenario_set_idx, run_idx, 
                                 decoded_params_template, instance, exec_path, recording_duration):
        """Executes a single test run within a scenario set."""
        # Copy the decoded parameters to the recorded parameters for this run
        # Make a deep copy to avoid modification issues across runs/sets
        current_run_decoded_params = json.loads(json.dumps(decoded_params_template))
        current_run_recorded_params = json.loads(json.dumps(decoded_params_template))

        scen_set_dir_name = f"set_{scenario_set_idx + 1}"
        run_dir_name = f"run_{run_idx}"
        
        run_specific_dir = os.path.join(base_dir, scen_set_dir_name, run_dir_name)
        self._makedirs_if_not_exists(run_specific_dir)

        print(f"Recording running process for {recording_duration} seconds before run {run_idx} in set {scenario_set_idx +1}\n")
        pre_run_processes = recording.record_all_process_info(duration=recording_duration)

        output_abs_path = os.path.abspath(run_specific_dir)
        
        if "OUTPUT" in self.scenario.outputs:
            output_filename = self.scenario.outputs['OUTPUT']
            output_file_abs_path = os.path.join(output_abs_path, output_filename)
            output_file_rel_path = os.path.join(scen_set_dir_name, run_dir_name, output_filename)
            current_run_decoded_params["OUTPUT"] = output_file_abs_path
            current_run_recorded_params["OUTPUT"] = output_file_rel_path

        command_params_for_exec = instance.get_exec_params(self.scenario.command, current_run_decoded_params, run_specific_dir)

        print()
        print(f"Running scenario set {scenario_set_idx+1}/run {run_idx} with params {command_params_for_exec}. Output saved on {run_specific_dir}")
        print(f"{exec_path} {command_params_for_exec}")
        print()
        
        exec_result = instance.execute_command(exec_path, command_params_for_exec)

        # Save detailed execution result for this run
        run_result_file_abs_path = os.path.join(output_abs_path, RUN_RESULT_JSON_FILENAME)
        run_result_file_rel_path = os.path.join(scen_set_dir_name, run_dir_name, RUN_RESULT_JSON_FILENAME)
        with open(run_result_file_abs_path, "w") as f:
            print(exec_result)
            json.dump(exec_result, f, indent=4)

        # Save pre-run process information for this run
        run_process_file_abs_path = os.path.join(output_abs_path, RUN_PROCESS_JSON_FILENAME)
        run_process_file_rel_path = os.path.join(scen_set_dir_name, run_dir_name, RUN_PROCESS_JSON_FILENAME)
        with open(run_process_file_abs_path, "w") as f:
            json.dump(pre_run_processes, f, indent=4)

        if "INPUT" in self.scenario.inputs:
            input_base_name = os.path.basename(self.scenario.inputs["INPUT"])
            input_copy_destination = os.path.join(output_abs_path, input_base_name)
            copied_input_file_rel_path = os.path.join(scen_set_dir_name, run_dir_name, input_base_name)
            shutil.copy(self.scenario.inputs["INPUT"], input_copy_destination)
            current_run_recorded_params["INPUT"] = copied_input_file_rel_path

        return {
            "parameters": current_run_recorded_params,
            "repeat": run_idx,
            "success": exec_result["success"],
            "start_time": exec_result["start_time"],
            "end_time": exec_result["end_time"],
            "exec_time": exec_result["end_time"] - exec_result["start_time"],
            "system_avg_cpu": exec_result["system_avg_cpu"],
            "system_avg_mem": exec_result["system_avg_mem"],
            # "process_avg_cpu": exec_result["process_avg_cpu"],
            # "process_avg_mem": exec_result["process_avg_mem"],
            "running_process": run_process_file_rel_path,
            "detailed_result": run_result_file_rel_path,
        }

    def _execute_all_test_runs(self, base_dir, instance, exec_path, recording_duration):
        """Executes all test runs for all scenario combinations."""
        all_runs_results = []
        print("Generating and executing test scenario runs\n")
        for scenario_set_idx, decoded_params_template in enumerate(self.scenario.combination):
            scen_set_dir = os.path.join(base_dir, f"set_{scenario_set_idx + 1}")
            self._makedirs_if_not_exists(scen_set_dir) # Ensure set directory exists

            for run_idx_within_set in range(1, self.scenario.repeat + 1):
                summarized_run_result = self._execute_single_test_run(
                    base_dir, scenario_set_idx, run_idx_within_set, 
                    decoded_params_template, instance, exec_path, recording_duration
                )
                all_runs_results.append(summarized_run_result)
                # Store the temporary/cumulative result to main json output file
                self.result["summarized_results"] = all_runs_results
                self._save_result()
        return all_runs_results

    def _save_benchmark_summary_to_csv(self, start_time_total, end_time_total):
        """Saves the overall benchmark summary to a CSV file."""
        execution_time_total = end_time_total - start_time_total
        start_time_hr = datetime.fromtimestamp(start_time_total).strftime('%Y-%m-%d %H:%M:%S')
        end_time_hr = datetime.fromtimestamp(end_time_total).strftime('%Y-%m-%d %H:%M:%S')

        record = {
            'test_name': self.scenario.name,
            'start_time': start_time_total,
            'end_time': end_time_total,
            'start_time_hr': start_time_hr,
            'end_time_hr': end_time_hr,
            'execution_time': execution_time_total
        }
        
        df = pd.DataFrame([record])
        try:
            existing_df = pd.read_csv(CSV_FILE)
            # Remove existing entry for the same test_name to prevent duplicates, then append
            existing_df = existing_df[existing_df['test_name'] != self.scenario.name]
            df = pd.concat([existing_df, df], ignore_index=True)
        except FileNotFoundError:
            pass # If file doesn't exist, the new df will create it
        
        df.to_csv(CSV_FILE, index=False)
        print(f'Test finished. Overall result for "{self.scenario.name}" saved to {CSV_FILE}.')

    # Run the benchmark according to methodology
    def run(self):
        base_dir = os.path.join(self.scenario.temp_directory, self.scenario.name)
        self._setup_environment(base_dir)
        self._record_initial_system_info()
        
        recording_duration = self._get_recording_duration()
        instance = command.get_instance(self.scenario)
        
        exec_path = self._perform_pre_run_diagnostics(instance, recording_duration)
        if not exec_path:
            print("Error: Execution path for the benchmark command not found. Aborting.")
            return

        start_time_total = time.time()
        
        # summarized_results_list will be stored in self.result by _execute_all_test_runs
        self._execute_all_test_runs(base_dir, instance, exec_path, recording_duration)
        
        end_time_total = time.time()
        
        self._save_benchmark_summary_to_csv(start_time_total, end_time_total)
        print(f"Benchmark run for '{self.scenario.name}' completed.")

    @classmethod
    def delete_test_result(cls, test_name):
        try:
            df = pd.read_csv(CSV_FILE)  # Use module-level constant
            df = df[df['test_name'] != test_name]
            df.to_csv(CSV_FILE, index=False) # Use module-level constant
            print(f'Test result for "{test_name}" deleted.')
        except FileNotFoundError:
            print(f'No results found to delete for "{test_name}".')

    @classmethod
    def list_all_results(cls):
        try:
            df = pd.read_csv(CSV_FILE) # Use module-level constant
            print(df)
        except FileNotFoundError:
            print('No results found.')
    
    @classmethod
    def get_test_instance(cls, test_name):
        try:
            df = pd.read_csv(CSV_FILE) # Use module-level constant
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