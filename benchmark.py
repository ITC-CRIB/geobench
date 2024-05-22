import os
import subprocess
import time
import pandas as pd
from datetime import datetime
import ansible_runner

class Benchmark:
    CSV_FILE = 'benchmark_results.csv'

    def run(self, test_name, script_file, input_dir, inventory_path, repeat=1):
        # Get base directory name
        dir_name = os.path.basename(input_dir)
        # Measure start time
        start_time = time.time()
        start_time_hr = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')

        # Running the playbook
        r = ansible_runner.interface.run(
            private_data_dir = 'ansible' ,
            playbook='run-scenario.yml',
            extravars={'src_dir': input_dir, 'repeat': repeat, 'script_file': script_file, 'scenario_name': test_name, 'dir_name': dir_name},
            inventory=inventory_path
        )

        # Measure end time
        end_time = time.time()
        end_time_hr = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')

        # Calculate execution time
        execution_time = end_time - start_time

        # Store results in CSV
        record = {
            'test_name': test_name,
            'start_time': start_time,
            'end_time': end_time,
            'start_time_hr': start_time_hr,
            'end_time_hr': end_time_hr,
            'execution_time': execution_time
        }
        
        df = pd.DataFrame([record])
        
        try:
            existing_df = pd.read_csv(self.CSV_FILE)
            existing_df = existing_df[existing_df['test_name'] != test_name]  # Remove existing entry if any
            df = pd.concat([existing_df, df], ignore_index=True)
        except FileNotFoundError:
            pass  # If file doesn't exist, we will create a new one
        
        df.to_csv(self.CSV_FILE, index=False)
        print(f'Test result for "{test_name}" saved.')

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