#!/usr/bin/env python3

import argparse
import datetime
import sys
import os
import shutil
import webbrowser

from .benchmark import Benchmark
from .error import MissingParameterError
from .report import PrometheusMetricsReporter

from . import scenario

class CommandLineTool:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Toolkit for benchmarking the geospatial processing workload")
        # self.parser.add_argument('-i', '--inventory', type=str, help='Inventory file', default='inventory.yml')
        self.subparsers = self.parser.add_subparsers(dest="command")

        # Create subparsers for "test" command
        self.run_parser = self.subparsers.add_parser("run", help='Run the benchmarking tests')
        # self.run_subparsers = self.test_parser.add_subparsers(dest="subcommand")
        # Subparser for the 'test run <scenario> <id>' subcommand
        # self.run_parser = self.run_subparsers.add_parser('run', help='Run the benchmarking test. test run <scenario_name> <scenario_path> ')
        self.run_parser.add_argument('-n','--name', type=str, help='The scenario unique name identifier')
        self.run_parser.add_argument('-d','--input-dir', type=str, help='Path of input directory in local computer')
        self.run_parser.add_argument('-f', '--file', type=str, help='Scenario file name')
        self.run_parser.add_argument('-r', '--repeat', type=int, help='The number of execution repeat', default=1)
        self.run_parser.add_argument('-c', '--converge', type=int, help='The number of converging percentage (in percent)', default=10)
        
        # Subparser for the 'result' subcommand
        self.result_parser = self.subparsers.add_parser('result', help='Manage benchmarking report result')
        # self.result_parser.add_argument('-n','--name', type=str, help='The scenario unique name identifier')
        self.result_subparsers = self.result_parser.add_subparsers(dest="subcommand")
        # Subparser for the 'result list' subcommand
        self.result_subparsers.add_parser('list', help='List all benchmarking scenario')
        # Subparser for the 'result remove <id>' subcommand
        self.result_remove_parser = self.result_subparsers.add_parser('remove', help='Delete benchmarking scenario given the scenario id')
        self.result_remove_parser.add_argument('id', type=str, help='The scenario id')
        # Subparser for the 'test save <id>' subcommand
        self.result_save_parser = self.result_subparsers.add_parser('save', help='Save benchmarking scenario artifacts to a specific local folder given the scenario id')
        self.result_save_parser.add_argument('id', type=str, help='The scenario id')
        self.result_save_parser.add_argument('--output-dir', type=str, help='The directory to save the scenario artifacts. Defaults to ~/geobench_saved_results/<scenario_id>.')
        # Subparser for the 'test save <id>' subcommand
        self.result_inspect_parser = self.result_subparsers.add_parser('inspect', help='Show benchmarking report result given the scenario id')
        self.result_inspect_parser.add_argument('id', type=str, help='The scenario id')
        # Subparser for the 'test display <id>' subcommand
        self.result_display_parser = self.result_subparsers.add_parser('display', help='Attempt to open a Grafana dashboard for the given scenario id')
        self.result_display_parser.add_argument('id', type=str, help='The scenario id')
        self.result_display_parser.add_argument('--grafana-url', type=str, default='http://18.197.58.197:9090', help='Base URL of the Grafana instance.')

        # Create subparsers for "install" command
        self.snapshot_parser = self.subparsers.add_parser("install", help='Install required packages')
        
        # Create subparsers for "monitor" command
        self.monitor_parser = self.subparsers.add_parser("monitor", help='Monitor the benchmarking')

    def run(self):
        args = self.parser.parse_args()
        # inventory_path = os.path.abspath(args.inventory)
        
        if args.command == 'run':
            self.handle_run(args)
        elif args.command == 'result':
            self.handle_result(args)
        elif args.command == 'install':
            self.handle_install(args)
        elif args.command == 'monitor':
            self.handle_monitor(args)
        else:
            self.parser.print_help()

    def handle_run(self, args, inventory_path=""):
        # Get the script file name
        scenario_file = os.path.abspath(args.file)

        try:
            # Load testing scenario
            test_scenario = scenario.load_scenario(scenario_file, args)
            # Run the bencmark based on parsed scenario
            benchmark = Benchmark(test_scenario)
            benchmark.run()
        except MissingParameterError as e:
            print(e)
            sys.exit(1)
    
    def handle_result(self, args):
        if args.subcommand == "list":
            Benchmark.list_all_results()
        elif args.subcommand == "inspect":
            scenario_id = args.id
            instance = Benchmark.get_test_instance(scenario_id)
            if instance is not None:
                test_name = instance["test_name"]
                start_time = datetime.datetime.fromtimestamp(instance["start_time"])
                end_time = datetime.datetime.fromtimestamp(instance["end_time"])
                print(f"Inspecting report for ID: {scenario_id}")
                print(f"Test name: {test_name}, Start time: {start_time}, End time: {end_time}")
                # TODO: Externalize this URL: "http://18.197.58.197:9090"
                # Ensure PrometheusMetricsReporter is correctly configured if this URL is parameterized
                reporter_url = args.grafana_url if hasattr(args, 'grafana_url') and args.subcommand == 'display' else "http://18.197.58.197:9090"
                reporter = PrometheusMetricsReporter(url=reporter_url, disable_ssl=True)
                reporter.generate_report(start_time=start_time, end_time=end_time, test_name=test_name)
            else:
                print(f"No test instance found for ID: {scenario_id}")

        elif args.subcommand == "remove":
            scenario_id = args.id
            try:
                Benchmark.delete_test_result(scenario_id)
                print(f"Successfully removed result and artifacts for scenario ID: {scenario_id}")
            except Exception as e:
                print(f"Error removing result for scenario ID {scenario_id}: {e}")

        elif args.subcommand == "save":
            scenario_id = args.id
            instance = Benchmark.get_test_instance(scenario_id)
            if not instance:
                print(f"No test instance found for ID: {scenario_id}. Cannot save.")
                return

            test_name = instance["test_name"]
            # Construct the source path based on how Benchmark structures its working directories
            # Benchmark.run creates scenario.working_dir as os.path.join("results", scenario.name, scenario.id)
            source_dir = os.path.join("results", test_name, scenario_id)

            if not os.path.isdir(source_dir):
                print(f"Source directory for artifacts not found: {source_dir}")
                return

            if args.output_dir:
                output_dir = os.path.abspath(args.output_dir)
            else:
                output_dir = os.path.abspath(os.path.join(os.path.expanduser("~"), "geobench_saved_results", scenario_id))
            
            try:
                os.makedirs(output_dir, exist_ok=True)
                # Copy the entire contents of the source_dir to output_dir
                # Python 3.8+ allows dirs_exist_ok=True for copytree
                shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)
                print(f"Successfully saved artifacts for scenario ID {scenario_id} to: {output_dir}")
            except Exception as e:
                print(f"Error saving artifacts for scenario ID {scenario_id} to {output_dir}: {e}")

        elif args.subcommand == "display":
            scenario_id = args.id
            instance = Benchmark.get_test_instance(scenario_id)
            if instance:
                test_name = instance["test_name"]
                start_time_ts = instance["start_time"]
                end_time_ts = instance["end_time"]
                
                start_ms = int(start_time_ts * 1000)
                end_ms = int(end_time_ts * 1000)
                
                # This is a generic Grafana URL pattern. Specific dashboards might vary.
                # Assuming a dashboard exists that can filter by a 'testname' variable or similar.
                # Users might need to adjust 'your-dashboard-uid/your-dashboard-name'.
                # For a more robust solution, dashboard UID and variable names could be configurable.
                grafana_dashboard_path = "/d/YOUR_DASHBOARD_UID/YOUR_DASHBOARD_NAME"
                grafana_link = f"{args.grafana_url.rstrip('/')}{grafana_dashboard_path}?orgId=1&from={start_ms}&to={end_ms}&var-testname={test_name}"
                
                print(f"Attempting to open Grafana for scenario ID {scenario_id} (Test: {test_name})")
                print(f"URL: {grafana_link}")
                try:
                    webbrowser.open_new_tab(grafana_link)
                except Exception as e:
                    print(f"Could not open web browser: {e}")
            else:
                print(f"No test instance found for ID: {scenario_id}. Cannot display.")
        else:
            self.result_parser.print_help()
    
    def handle_install(self, args):
        print(f"Attempting to run installation process...")
        try:
            import ansible_runner # Make sure ansible_runner is installed
            
            # Define paths relative to the geobench package directory
            base_dir = os.path.dirname(__file__) # geobench directory
            ansible_dir = os.path.join(base_dir, 'ansible')
            inventory_file = os.path.join(ansible_dir, 'inventory.yml')
            playbook_file = os.path.join(ansible_dir, 'install.yml')

            if not os.path.isdir(ansible_dir):
                print(f"Ansible directory not found: {ansible_dir}")
                print("Please ensure an 'ansible' directory with 'inventory.yml' and 'install.yml' exists within the geobench package.")
                return
            if not os.path.exists(inventory_file):
                print(f"Inventory file not found: {inventory_file}")
                return
            if not os.path.exists(playbook_file):
                print(f"Playbook file not found: {playbook_file}")
                return

            print(f"Running Ansible playbook: {playbook_file} with inventory: {inventory_file}")
            r = ansible_runner.interface.run(
                    private_data_dir=ansible_dir, # Directory for ansible artifacts
                    playbook=playbook_file,
                    inventory=inventory_file
                )
            
            print(f"Ansible run completed. Status: {r.status}, RC: {r.rc}")
            if r.rc != 0:
                print(f"Ansible playbook execution failed. See logs in {os.path.join(ansible_dir, 'artifacts')}")
            else:
                print("Installation playbook executed successfully.")

        except ImportError:
            print("ansible_runner package is not installed. Please install it to use this feature (e.g., 'pip install ansible-runner').")
        except Exception as e:
            print(f"An error occurred during the install process: {e}")

    def handle_monitor(self, args):
        # This is a placeholder. Actual monitoring depends on the deployed infrastructure.
        # It typically involves checking a dashboarding tool like Grafana.
        default_grafana_url = 'http://18.197.58.197:9090' # Consistent with other defaults
        print(f"Handling monitor command...")
        print(f"Geobench monitoring typically involves observing system and application metrics.")
        print(f"If you have a Grafana instance set up for monitoring, you might find dashboards at an address like: {default_grafana_url}")
        print(f"You may need to navigate to specific dashboards relevant to your benchmarks.")
        print("For real-time process monitoring during a 'run' command, Geobench collects metrics directly.")
        print("This 'monitor' command is a hint for post-run or general system observation.")

def main():
    tool = CommandLineTool()
    tool.run()

if __name__ == "__main__":
    main()
