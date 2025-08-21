Existing state:
- User can define the scenario as `yaml` file. User can define several configurations:
    * The number of repetitions
    * Type of execution (qgis-python, qgis-process, ordinary python script, or shell script)
    * Execution parameters specific to each workflow
- Benchmark tool supports three types of execution: 
    * QGIS process with user-defined and auto-discovery of QGIS binary path
    * QGIS python with auto-generated python code and auto-discovery its virtual environment 
    * Python script with virtual environment support
    * Shell script with working directory definition
- The tool records execution and resource utilizations data during execution: CPU utilization both overall and per-CPU (%), memory utilization (%), and I/O activities. The data is recorded on both system level and per-process level. The tool is able to track every sub processes created during the workflow execution. The process tracking is performed efficiently using combination of asyncio and multi-threading.
- Tool is able to record the resource (CPU and memory) utilizations of workflow-related processes as log. 
- During start and finish of a command execution, the tool also recors other processes as log (record at the end of each step).
- Tool generates summarized as well as detailed report as interactive HTML pages.

To-do
- Generate single and downloadable HTML report (using plotly) instead of multiple HTML files with separated JSON output. The downside of this approach is the size of single HTML file will be quite big.
- From the user perspective, it would be good to highlight the 
- Nicely visualize the process's log data especially if we deals with information coming from multiple processes.
- Change the name of geobench as it is already used by LLM geo foundation model benchmarking (https://geobench.org)
- Improve the Readme (and possibly more comprehensive documentation if time allows)

Notes 21082025:
- Change the Python version to be more relaxed
- Only list the main requirement
- Use the standard Python dveelopment instead of `uv`
- The timestamp is not useful, use time step (lets say start from 0,1,2)
- The legend is too big (see the first right of detailed charts)
- Use interactive graph
- Provide profiling information up to the function level. Use cProfile as an optional (only for Python-based workflow).
- Single html file, interactive graph, provide the raw data (in JSON), provide a link to raw json file data.
