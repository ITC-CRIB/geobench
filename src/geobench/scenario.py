import itertools
import os
import re
import yaml

from .error import MissingParameterError


class Scenario:
    """Defines the scenario structure."""
    def __init__(
        self,
        name: str,
        repeat: int,
        type: str,
        command: str,
        command_file: str,
        inputs,
        outputs,
        temp_directory: str,
        parameters,
        scenario_combination,
        venv: str,
        working_dir: str,
    ):
        self.name = name
        self.repeat = repeat
        self.type = type
        self.command = command
        self.command_file = command_file
        self.inputs = inputs
        self.outputs = outputs
        self.temp_directory = temp_directory
        self.parameters = parameters
        self.combination = scenario_combination
        self.venv = venv
        self.working_dir = working_dir


    def __repr__(self):
        return (f"Scenario(name={self.name}, repeat={self.repeat}, type={self.type}, "
                f"command={self.command}, command_file={self.command_file}, inputs={self.inputs}, "
                f"outputs={self.outputs}, temp_directory={self.temp_directory}, "
                f"parameters={self.parameters}, scenarios={self.combination})")


def generate_scenarios(parameters: dict):
    if not parameters:
        return [{}]

    parameters = {
        key: val if isinstance(val, list) else [val]
        for key, val in parameters.items()
    }

    keys, vals = zip(*parameters.items())
    scenarios = [dict(zip(keys, combination)) for combination in itertools.product(*vals)]

    return scenarios


def load_scenario(yaml_file, cmd_args):
    with open(yaml_file, 'r') as file:
        scenario_data = yaml.safe_load(file)

    name = cmd_args.name or scenario_data.get('name')
    repeat = cmd_args.repeat or scenario_data.get('repeat', 1)
    type = scenario_data.get('type')
    command = scenario_data.get('command')
    command_file = scenario_data.get('command-file')
    inputs = scenario_data.get('inputs', {})
    outputs = scenario_data.get('outputs', {})
    temp_directory = scenario_data.get('temp-directory')
    parameters = scenario_data.get('parameters', {})
    venv = scenario_data.get('venv')
    working_dir = scenario_data.get('workdir', os.getcwd())

    checked_inputs = {key: os.path.abspath(val) for key, val in inputs.items()}

    if isinstance(parameters, dict):
        all_parameters = parameters | checked_inputs | outputs

    elif isinstance(parameters, list):
        all_parameters = {} | checked_inputs | outputs

    scenarios = generate_scenarios(all_parameters)

    if not name:
        raise ValueError("Missing scenario name.")

    if type not in ['qgis-process', 'qgis-python', 'qgis-json', 'python', 'shell']:
        raise ValueError(f"Invalid scenario type '{type}'.")

    return Scenario(
        name=name,
        repeat=repeat,
        type=type,
        command=command,
        command_file=command_file,
        inputs=checked_inputs,
        outputs=outputs,
        temp_directory=temp_directory,
        parameters=parameters,
        scenarios=scenarios,
        venv=venv,
        working_dir=working_dir
    )
