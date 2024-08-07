# GeoBench

GeoBench is a tool designed to benchmark geospatial software. It allows users to run benchmarks based on scenarios specified in YAML files. This project is currently under development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Operating System**: Linux, Windows (with WSL2 or Powershell), MacOS
- **Python**: Python 3 with the `pip` package manager installed

## Preparation

Follow these steps to set up GeoBench:

- **Clone the repository**:
   ```bash
   git clone https://github.com/ITC-CRIB/geobench
   cd geobench
   ```

- **Pull the repository**:
   ```bash
   cd geobench
   git pull
   ```

- For **Windows** user, specify the directory location of your QGIS installation directory. Open **Terminal** program, and set the directory location of QGIS in `QGIS_PATH`environment variable. 
	- If you are using Command-Line
		```
		set QGIS_PATH="C:\Program Files\QGIS 3.34.9"
		```
	- If you are using PowerShell
		```
	   $env:QGIS_PATH="C:\Program Files\QGIS 3.34.9"
	   ```

## Installation as Tool

- Install `pipx`
	```
	pip install pipx
	```

- Run the installation process
	```
	pipx install . --force
	```

- Update program path to be recognized in system
	```
	pipx ensurepath
	```

- Note: to update the tool, you need to pull from github and do the installation again.

## Development
- **Set up and activate the Python environment**:
   - **Using `venv`**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate   # On Windows, use `.venv\Scripts\activate`
     ```

   - **Using `virtualenv`**:
     ```bash
     pip install virtualenv
     virtualenv .venv
     source .venv/bin/activate   # On Windows, use `.venv\Scripts\activate`
     ```

- **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```
   
- During development, create two directories: `sample-input` and `sample-output`. Both directories will be ignored from Git push and pull activities.
	```
	mkdir sample-input
	mkdir sample-output
	```
- You can copy the example shapefile as input in `sample-input` directory.

- To run the program during development (without installing it as tool), you can execute following command:
	```
	python -m geobench.main run -f sample-input/example-scenario.yaml
	```

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
	geobench run -f sample-input/example-scenario.yaml
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
	geobench run -f sample-input/example-scenario-python.yaml
	```
---

Feel free to contribute to the development of GeoBench by submitting issues or pull requests on the repository. For more details on contributing, please refer to the CONTRIBUTING.md file in the repository.