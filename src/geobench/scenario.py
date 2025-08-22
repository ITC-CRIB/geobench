import inspect
import itertools
import json
import os
import re
import shutil
import time
import yaml

from .cache import clear_cache
from .executor.factory import create_executor
from .system import get_system_info, monitor_system


import logging
logger = logging.getLogger(__name__)


class Scenario:
    """Scenario class."""

    def __init__(
        self,
        type: str,
        name: str,
        command: str,
        inputs: list | dict=None,
        outputs: list | dict=None,
        arguments: list | dict=None,
        repeat: int=1,
        idle_time: float=10.0,
        workdir: str=None,
        basedir: str=None,
        outdir: str=None,
        venv: str=None,
    ):
        """Initializes scenario object.

        Args:
            type (str): Scenario type.
            name (str): Scenario name.
            command (str): Command.
            inputs (list | dict): Dictionary of inputs (optional).
            outputs (list | dict): Dictionary of outputs (optional).
            arguments (list | dict): Arguments (optional).
            repeat (int): Number of repetations (default = 1).
            idle_time (int): Idle time between runs (s) (default = 10.0).
            workdir (str): Working directory path (default = current working directory).
            basedir (str): Base directory path (default = current working directory).
            outdir (str): Output directory path (default = generated from name)
            venv (str): Virtual environment path (optional).

        Raises:
            ValueError: if invalid scenario type.
            ValueError: if empty scenario name.
            ValueError: if empty command.
            ValueError: if invalid arguments.
            ValueError: if invalid inputs.
            ValueError: if invalid outputs.
        """
        if type not in ['qgis-process', 'qgis-python', 'python', 'shell']:
            raise ValueError("Invalid scenario type.", type)

        if not name:
            raise ValueError("Empty scenario name.")

        if not command:
            raise ValueError("Empty command.")

        if arguments and not isinstance(arguments, (list, dict)):
            raise ValueError("Invalid arguments.")

        if inputs and not isinstance(inputs, (list, dict)):
            raise ValueError("Invalid inputs.")

        if outputs and not isinstance(outputs, (list, dict)):
            raise ValueError("Invalid outputs.")

        self.type = type
        self.name = name
        self.command = command
        self.inputs = inputs or {}
        self.outputs = outputs or {}
        self.arguments = arguments or {}
        self.repeat = repeat or 1
        self.idle_time = idle_time or 0.0

        cwd = os.getcwd()

        self.workdir = workdir or cwd
        if not os.path.isabs(self.workdir):
            self.workdir = os.path.join(cwd, self.workdir)
            if not os.path.isdir(self.workdir):
                raise ValueError("Invalid working directory.", workdir)

        self.basedir = basedir or cwd
        if not os.path.isabs(self.basedir):
            self.basedir = os.path.join(cwd, self.basedir)
            if not os.path.isdir(self.basedir):
                raise ValueError("Invalid base directory.", basedir)

        self.outdir = outdir or re.sub(r'-+', '-', re.sub(r'[^\w-]', '-', name.lower())).strip('-')
        if not os.path.isabs(self.outdir):
            self.outdir = os.path.join(self.basedir, self.outdir)

        self.venv = venv
        if self.venv:
            if not os.path.isabs(self.venv):
                self.venv = os.path.join(cwd, self.venv)
            if not os.path.isdir(self.venv):
                raise ValueError("Invalid virtual environment.", venv)

        if isinstance(self.outputs, dict):
            outputs = list(self.outputs.values())
        else:
            outputs = self.outputs

        if not all(isinstance(item, str) for item in outputs):
            raise ValueError("Invalid outputs.")

        multi_input = isinstance(self.inputs, dict)

        if isinstance(self.arguments, list):
            args = {key: val for key, val in enumerate(self.arguments)}
        else:
            args = self.arguments

        args = args | (self.inputs if multi_input else {})
        args = {
            key: val if isinstance(val, list) else [val]
            for key, val in args.items()
        }

        if args:
            keys, vals = zip(*args.items())
            sets = [dict(zip(keys, items)) for items in itertools.product(*vals)]

        else:
            sets = [{}]

        self.sets = []
        for args in sets:
            data = {}

            if multi_input:
                data['inputs'] = [args[key] for key in self.inputs.keys()]
            else:
                data['inputs'] = self.inputs if isinstance(self.inputs, list) else [self.inputs]

            data['outputs'] = outputs
            if isinstance(self.outputs, dict):
                args.update(self.outputs)

            data['arguments'] = args

            self.sets.append(data)


    def _store(self, filename: str, content: dict):
        path = os.path.join(self.outdir, filename)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(content, file, indent=2)


    def _store_result(self, result: dict):
        self._store('result.json', result)


    def benchmark(self, clean: bool=False):
        """Performs benchmarking of the scenario."""
        result = {}

        try:
            print("Running scenario {}.".format(self.name))

            print("Creating executor.")
            executor = create_executor(self)

            print("Setting up output directory.")
            if os.path.exists(self.outdir):
                if os.path.isdir(self.outdir):
                    if not clean:
                        print("Output directory exists, aborting.")
                        return {}
                    else:
                        logger.debug(f"Removing existing output directory {self.outdir}.")
                        shutil.rmtree(self.outdir)
                else:
                    print("Invalid output directory, aborting.")
                    return {}
            os.makedirs(self.outdir)

            print("Clearing system caches.")
            clear_cache()

            print("Storing executor configuration.")
            result['config'] = executor.config
            self._store_result(result)

            print("Storing system information.")
            result['system'] = get_system_info()
            self._store_result(result)

            print("Baseline monitoring for {} s.".format(self.idle_time))
            result['baseline'] = monitor_system(self.idle_time)
            self._store_result(result)

            num_sets = len(self.sets)

            print("Executing {} scenario set(s) with {} repeat(s).".format(num_sets, self.repeat))
            start_time = time.time()

            len_sets = len(str(num_sets))
            len_runs = len(str(self.repeat))

            for i, data in enumerate(self.sets):
                set_id = i + 1

                for j in range(self.repeat):
                    run_id = j + 1

                    path = os.path.join(
                        f"set_{set_id:0{len_sets}d}",
                        f"run_{run_id:0{len_runs}d}",
                    )

                    abs_path = os.path.join(self.outdir, path)
                    os.makedirs(abs_path, exist_ok=True)

                    result_path = os.path.join(abs_path, 'result.json')

                    print("Executing scenario set {}, run {}.".format(set_id, run_id))

                    args = executor.get_arguments(self.command, data['arguments'])

                    out = executor.execute(args)

                    out.update({
                        'set': set_id,
                        'run': run_id,
                    })
                    self._store(result_path, out)

                    print("Endline monitoring for {} s.".format(self.idle_time))
                    out['endline'] = monitor_system(self.idle_time)
                    self._store(result_path, out)

            duration = time.time() - start_time

            print("{} run(s) completed in {} s.".format(num_sets, duration))

        except KeyboardInterrupt:
            print("Benchmark run interrupted by user.")

        except Exception as err:
            raise


def load_scenario(path, **kwargs):
    """Loads scenario from a YAML file and customizes it if required.

    Args:
        path (str): Path of the YAML file.
        **kwargs: Custom scenario parameters.

    Returns:
        Scenario object.
    """
    logger.debug(f"Loading scenario from {path}.")
    with open(path, 'r', encoding='utf-8') as file:
        scenario = yaml.safe_load(file)

    logger.debug(f"Updating scenario with {kwargs}.")
    scenario.update(kwargs)

    if scenario.get('outputs') and not isinstance(scenario['outputs'], (list, dict)):
        scenario['outputs'] = [scenario['outputs']]

    if not scenario.get('name'):
        scenario['name'] = os.path.splitext(os.path.basename(path))[0]

    args = {}
    for key in inspect.signature(Scenario.__init__).parameters.keys():
        val = scenario.get(key)
        if key != 'self' and val is not None:
            args[key] = val

    return Scenario(**args)
