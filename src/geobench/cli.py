"""Command line interface module."""

import argparse
import ast
import logging
import os
import sys
from typing import Any

from .executor import get_executors
from .executor.program import ProgramExecutor
from .scenario import Scenario
from .utils import prune_dict

logger = logging.getLogger(__name__)


class ArgumentDefaultsHelpFormatterNoNone(argparse.ArgumentDefaultsHelpFormatter):
    """Argument help formatter that omits empty default values."""

    def _get_help_string(self, action):
        if action.default is None:
            return action.help
        return super()._get_help_string(action)


class KeyValueAction(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        values = getattr(namespace, self.dest, None) or {}
        key, value = value.split("=", 1)
        values[key] = value
        setattr(namespace, self.dest, values)


class ConfigOptionAction(argparse.Action):
    """Parse and combine repeated key=value configuration options."""

    def __init__(
        self,
        option_strings: list[str],
        dest: str,
        nargs: str | int | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("default", {})
        super().__init__(option_strings, dest, nargs, **kwargs)
        self._values: dict[Any, set[Any]] = {}

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        value: str,
        option_string: str | None = None,
    ) -> None:
        try:
            key, val = value.split("=", 1)
        except ValueError:
            raise argparse.ArgumentError(self, "argument must be in key=value format")

        try:
            val = ast.literal_eval(val)
        except ValueError:
            pass
        except SyntaxError:
            raise argparse.ArgumentError(self, "value must be a valid literal")

        try:
            key = int(key)
        except ValueError:
            pass

        values = self._values.setdefault(key, set())

        if isinstance(val, (list, tuple, set)):
            values.update(val)
        else:
            values.add(val)

        setattr(
            namespace,
            self.dest,
            {key: sorted(values) for key, values in self._values.items()},
        )


class CLI:
    """Command line interface class."""

    def add_arguments(self, executor_cls, parser, all_optional: bool = False):
        """Add arguments to the parser."""
        for name, option in executor_cls.get_options().items():
            kwargs = {}
            if option.positional:
                flag = name
                if not option.required or all_optional:
                    kwargs["nargs"] = "?"
            else:
                flag = f"--{name}"
                if option.type == dict:
                    kwargs["action"] = KeyValueAction
                else:
                    kwargs["type"] = option.type
            parser.add_argument(
                flag,
                help=option.description,
                default=option.default,
                **kwargs,
            )

    def __init__(self):
        """Initialize command line interface object."""

        self.parser = argparse.ArgumentParser(
            description="Benchmarking toolkit for geospatial processing workflows.",
            formatter_class=ArgumentDefaultsHelpFormatterNoNone,
        )

        subparsers = self.parser.add_subparsers(
            dest="cli_command",
            required=True,
            metavar="COMMAND",
        )

        # Common arguments

        common_parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=ArgumentDefaultsHelpFormatterNoNone,
        )

        common_parser.add_argument(
            "-n",
            "--name",
            type=str,
            help="Benchmark name",
        )
        common_parser.add_argument(
            "-r",
            "--repeat",
            type=int,
            help="Number of repeats (default: 1)",
        )
        common_parser.add_argument(
            "-w",
            "--wait",
            type=float,
            help="Idle wait time before each run, in seconds (default: 5.0)",
        )
        common_parser.add_argument(
            "-m",
            "--monitor",
            type=float,
            help="Monitoring duration before and after each run, in seconds (default: 5.0)",
        )
        common_parser.add_argument(
            "-i",
            "--input",
            dest="inputs",
            action="append",
            help="Input file argument or position (can be repeated)",
            default=[],
        )
        common_parser.add_argument(
            "-a",
            "--arg",
            dest="arguments",
            action=ConfigOptionAction,
            help="Argument as key=value (can be repeated)",
        )
        common_parser.add_argument(
            "-o",
            "--output",
            dest="outputs",
            action="append",
            help="Output file argument or position (can be repeated)",
            default=[],
        )
        common_parser.add_argument(
            "--archive",
            type=str,
            choices=["none", "both", "input", "output"],
            help="File types to archive (default: output)",
        )
        common_parser.add_argument(
            "--basedir",
            type=str,
            help="Base directory (default: current working directory)",
        )
        common_parser.add_argument(
            "--outdir",
            type=str,
            help="Output directory (default: autogenerated from the scenario name)",
        )
        common_parser.add_argument(
            "--clear-outdir",
            action="store_true",
            help="Clear the output directory",
        )
        common_parser.add_argument(
            "--clear-outputs",
            action="store_true",
            help="Clear the output files",
        )
        common_parser.add_argument(
            "--clear-cache",
            action=argparse.BooleanOptionalAction,
            help="Clear the system caches (default: True)",
        )
        common_parser.add_argument(
            "-d",
            "--debug",
            dest="cli_debug",
            action="store_true",
            help="Enable debug mode",
        )

        # Run command

        run_parser = subparsers.add_parser(
            "run",
            help="Run a benchmark.",
            parents=[common_parser],
        )

        run_subparsers = run_parser.add_subparsers(
            dest="executor", required=True, metavar="EXECUTOR"
        )

        # Scenario subcommand

        scenario_parser = run_subparsers.add_parser(
            "scenario",
            help="Pre-defined Scenario",
            parents=[common_parser],
        )

        scenario_parser.add_argument(
            "filename",
            help="Scenario filename (YAML)",
        )

        # Executor subcommands

        for code, executor_cls in get_executors().items():
            if not issubclass(executor_cls, ProgramExecutor):
                continue

            info = executor_cls.get_info()

            executor_parser = run_subparsers.add_parser(
                code, help=info.name, parents=[common_parser]
            )

            self.add_arguments(executor_cls, executor_parser)

        # Help command

        help_parser = subparsers.add_parser(
            "help",
            help="Display help on a specific executor.",
        )

        help_subparsers = help_parser.add_subparsers(
            dest="executor",
            required=True,
            metavar="EXECUTOR",
        )

        for code, executor_cls in get_executors().items():
            if not hasattr(executor_cls, "get_help"):
                continue

            info = executor_cls.get_info()

            executor_parser = help_subparsers.add_parser(code, help=info.name)

            self.add_arguments(executor_cls, executor_parser, all_optional=True)

    def run(self):
        """Run command line interface."""
        args = self.parser.parse_args()

        if args.cli_command == "help":
            executor_cls = get_executors().get(args.executor)
            config = prune_dict(
                {
                    key: getattr(args, key)
                    for key in executor_cls.get_options()
                    if hasattr(args, key)
                }
            )
            executor = executor_cls(config, no_check=True)
            help = executor.get_help()
            print(help)
            sys.exit()

        if args.cli_debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

            for name in logging.root.manager.loggerDict:
                if name.startswith("geobench"):
                    logging.getLogger(name).setLevel(logging.DEBUG)

            logger.debug("Debugging enabled")
        else:
            logging.basicConfig(
                level=logging.INFO, format="%(levelname)s - %(message)s"
            )

        kwargs = prune_dict(
            {
                key: value
                for key, value in vars(args).items()
                if not key.startswith("cli_")
            }
        )

        if args.executor == "scenario":
            del kwargs["executor"]
            logger.debug("Loading scenario from %s", args.filename)
            scenario = Scenario.load(os.path.abspath(args.filename), **kwargs)

        else:
            logger.debug("Creating scenario from command line arguments")
            executor_cls = get_executors().get(args.executor)
            config = prune_dict(
                {
                    key: getattr(args, key)
                    for key in executor_cls.get_options()
                    if hasattr(args, key)
                }
            )
            for key in config:
                del kwargs[key]
            kwargs["config"] = config

            scenario = Scenario(**kwargs)

        try:
            scenario.benchmark()

        except RuntimeError as err:
            print(str(err))
            sys.exit(1)


def main():
    """Run command line interface."""
    cli = CLI()
    cli.run()
