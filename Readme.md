# GeoBench

GeoBench is a tool designed to benchmark geospatial software. It allows users to run benchmarks based on scenarios specified in YAML files. This project is currently under development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Operating System**: Linux, Windows (with WSL2 or Powershell), MacOS
- **Python**: Python 3 with the `pip` package manager installed

## Installation

Follow these steps to set up GeoBench:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ITC-CRIB/geobench
   cd geobench
   ```
2. **Pull the repository**:
   ```bash
   cd geobench
   git pull
   ```

3. **Set up and activate the Python environment**:
   - **Using `venv`**:
     ```bash
     python3 -m venv venv
     source .venv/bin/activate   # On Windows, use `venv\Scripts\activate`
     ```

   - **Using `virtualenv`**:
     ```bash
     pip install virtualenv
     virtualenv .venv
     source .venv/bin/activate   # On Windows, use `venv\Scripts\activate`
     ```

4. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```
5. For **Windows** user, specify the directory location of your QGIS installation directory. Open **Terminal** program, and set the directory location of QGIS in `QGIS_PATH`environment variable. For example
   ```
   setx QGIS_PATH="C:\Program Files\QGIS 3.34.9"
   ```

6. During development, create two directories: `sample-input` and `sample-output`. Both directories will be ignored from Git push and pull activities.
   ```
   mkdir sample-input
   mkdir sample-output
   ```
7. You can copy the example shapefile as input in `sample-input` directory.

## Running Benchmarking Scenario
A benchmarking scenario is represented in a YAML file. For the time being, there are two scenario types supported in this tool: `qgis-command` and `qgis-python`. The `qgis-json` and `arcgis-command` will be supported later.

### Running qgis-command scenario type
In this scenario type, the QGIS benchmarking is performed by running `qgis_process` command in terminal. The sample scenario file can be accessed in `example/qgis-command/example-scenario.yaml`.

- Copy the sample scenario to directory `sample-input`
   ```
   cp example/qgis-command/example-scenario.yaml sample-input/example-scenario.yaml
   ```
- Modify the parameter in the YAML file. Make sure the `INPUT` and `OUTPUT` paths are exist and accessible.
- To run the benchmark, use the following command:

```bash
python3 geobench run -f sample-input/example-scenario.yaml
```

### Running qgis-python scenario type
In this scenario type, the QGIS benchmarking is performed by running QGIS python code specified by user. The sample code and scenario files can be accessed in `example/qgis-command/example-scenario.yaml`.

- Copy the sample scenario to directory `sample-input`
   ```
   cp example/qgis-python/example-scenario-python.yaml sample-input/example-scenario-python.yaml
   ```
- Copy the sample code and scenario files to directory `sample-input`
   ```
   cp example/qgis-python/example-scenario-python.yaml sample-input/example-scenario-python.yaml
   cp example/qgis-python/program.py sample-input/program.py
   ```
- Modify the Python code. For **Windows** user, make sure you define the right path on the QGIS_PATH variable. 
- Modify the YAML file. Make sure the `INPUT` and `OUTPUT` paths are exist and accessible.
- To run the benchmark, use the following command:

```bash
python3 geobench run -f sample-input/example-scenario-python.yaml
```
---

Feel free to contribute to the development of GeoBench by submitting issues or pull requests on the repository. For more details on contributing, please refer to the CONTRIBUTING.md file in the repository.