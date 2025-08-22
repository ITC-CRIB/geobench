import argparse
import os
import sys

from .scenario import load_scenario


import logging
logger = logging.getLogger(__name__)


class CLI:
    """Command line interface class."""

    def __init__(self):
        """Initializes command line interface object."""

        self.parser = argparse.ArgumentParser(description="Benchmarking toolkit for geospatial processing workflows.")
        self.parser.add_argument('filename', type=str, help='Scenario filename.')
        self.parser.add_argument('-n','--name', type=str, help='Scenario name.')
        self.parser.add_argument('-r', '--repeat', type=int, help='Number of repeats.')
        self.parser.add_argument('-c', '--clean', action='store_true')
        self.parser.add_argument('-d', '--debug', action='store_true')
        # TODO: Add more scenario arguments for further customization.


    def run(self):
        """Runs command line interface."""
        args = self.parser.parse_args()

        if args.debug:
            logging.basicConfig(level=logging.DEBUG)

            for name in logging.root.manager.loggerDict:
                if name.startswith('geobench'):
                    logging.getLogger(name).setLevel(logging.DEBUG)

            logger.debug("Debugging enabled.")

        try:
            kwargs = {
                key: val for key, val in vars(args).items()
                if val is not None
            }

            scenario = load_scenario(os.path.abspath(args.filename), **kwargs)
            scenario.benchmark(clean=args.clean)

        except Exception as err:
            # print(err)
            # sys.exit(1)
            raise


def main():
    """Runs command line interface."""
    cli = CLI()
    cli.run()
