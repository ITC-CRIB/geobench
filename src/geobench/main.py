import argparse
import datetime
import os
import shutil
import sys

from .benchmark import Benchmark
from .error import MissingParameterError

from . import scenario


class CommandLineTool:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Toolkit for benchmarking the geospatial processing workload")
        self.subparsers = self.parser.add_subparsers(dest="command")

        # Create subparser for "run" command
        self.run_parser = self.subparsers.add_parser("run", help='Run the benchmarking tests')
        self.run_parser.add_argument('-n','--name', type=str, help='The scenario unique name identifier')
        self.run_parser.add_argument('-d','--input-dir', type=str, help='Path of input directory in local computer')
        self.run_parser.add_argument('-f', '--file', type=str, help='Scenario file name')
        self.run_parser.add_argument('-r', '--repeat', type=int, help='The number of execution repeat', default=1)
        self.run_parser.add_argument('-c', '--converge', type=int, help='The number of converging percentage (in percent)', default=10)

        # Create subparser for "result" command
        self.result_parser = self.subparsers.add_parser('result', help='Manage benchmarking report result')
        self.result_subparsers = self.result_parser.add_subparsers(dest="subcommand")

        # Create subparser for "result list" subcommand
        self.result_subparsers.add_parser('list', help='List all benchmarking scenario')

        # Create subparser for "result remove <id>" subcommand
        self.result_remove_parser = self.result_subparsers.add_parser('remove', help='Delete benchmarking scenario given the scenario id')
        self.result_remove_parser.add_argument('id', type=str, help='The scenario id')

        # Create subparser for "result save <id>" subcommand
        self.result_save_parser = self.result_subparsers.add_parser('save', help='Save benchmarking scenario artifacts to a specific local folder given the scenario id')
        self.result_save_parser.add_argument('id', type=str, help='The scenario id')
        self.result_save_parser.add_argument('--output-dir', type=str, help='The directory to save the scenario artifacts. Defaults to ~/geobench_saved_results/<scenario_id>.')


    def run(self):
        args = self.parser.parse_args()

        if args.command == 'run':
            self.handle_run(args)

        elif args.command == 'result':
            self.handle_result(args)

        else:
            self.parser.print_help()


    def handle_run(self, args):
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
            Benchmark.list_results()

        elif args.subcommand == "remove":
            scenario_id = args.id
            try:
                Benchmark.remove_result(scenario_id)
                print(f"Successfully removed result and artifacts for scenario {scenario_id}.")

            except Exception as e:
                print(f"Error removing result and artifacts for scenario {scenario_id}: {e}.")

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

        else:
            self.result_parser.print_help()


def main():
    tool = CommandLineTool()
    tool.run()
