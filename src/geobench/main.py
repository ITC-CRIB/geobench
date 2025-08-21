import argparse
import os
import sys

from .benchmark import Benchmark
from .scenario import load_scenario


class CommandLineTool:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Benchmarking toolkit for geospatial processing workflows.")
        self.parser.add_argument('filename', type=str, help='Scenario filename.')
        self.parser.add_argument('-n','--name', type=str, help='Scenario name.')
        self.parser.add_argument('-r', '--repeat', type=int, help='Number of repeats.', default=1)


    def run(self):
        args = self.parser.parse_args()

        path = os.path.abspath(args.filename)

        try:
            scenario = load_scenario(path, args)

            benchmark = Benchmark(scenario)
            benchmark.run()

        except Exception as err:
            print(err)
            sys.exit(1)


def main():
    tool = CommandLineTool()
    tool.run()
