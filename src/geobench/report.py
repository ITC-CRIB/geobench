#%%
import json
import statistics
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
from typing import Dict, List, Any

def calculate_run_summary(run_result: dict) -> dict:
    """Calculate summary statistics from single run result.

    Args:
        run_result (dict): The run result data.

    Returns:
        dict: A dictionary containing the summary statistics.
    """
    summary = {
        # "set": run_result.get("set", 0),
        "run": run_result.get("run", 0),
        # "arguments": run_result.get("arguments", {}),
        "running_time": 0,
        "success": run_result.get("success", False),
        "start_time": run_result.get("start_time", 0),
        "end_time": run_result.get("end_time", 0),
        "avg_system_cpu": [],
        "avg_system_memory": {},
        "num_processes": 0,
        "processes": {}
    }
    # Calculate Average per-core system CPU usage
    system_per_cpu_list = []
    if run_result["system"]:
        for system_data in run_result["system"]:
            for i, cpu_percent in enumerate(system_data["cpu_percent"]):
                if i >= len(system_per_cpu_list):
                    system_per_cpu_list.append([])
                if cpu_percent is not None:
                    system_per_cpu_list[i].append(cpu_percent)
        for cpu_usage in system_per_cpu_list:
            avg_cpu = statistics.mean(cpu_usage) if cpu_usage else 0.0
            summary["avg_system_cpu"].append(avg_cpu)

    # Calculate Average per-type system memory usage
    system_memory_dict = {}
    if run_result["system"]:
        for system_data in run_result["system"]:
            for type, mem_usage in system_data["memory_usage"].items():
                if type not in system_memory_dict:
                    system_memory_dict[type] = []
                if mem_usage is not None:
                    system_memory_dict[type].append(mem_usage)
        for type, mem_usage in system_memory_dict.items():
            avg_mem = statistics.mean(mem_usage) if mem_usage else 0.0
            summary["avg_system_memory"][type] = avg_mem

    if "starting_time" in run_result and "ending_time" in run_result:
        summary["running_time"] = run_result["ending_time"] - run_result["starting_time"]

    process_stats = {}
    if run_result["processes"]:
        summary["num_processes"] = len(run_result["processes"])
        for pid, process_info in run_result.get("processes", {}).items():
            if "metrics" in process_info:
                process_metrics = process_info["metrics"]

                cpu_timeline = []
                memory_timeline = []
                thread_timeline = []
                step_timeline = []

                for m in process_metrics:
                    if (step := m.get("step", None)) is not None:
                        step_timeline.append(step)
                    if (cpu := m.get("cpu_percent", None)) is not None:
                        cpu_timeline.append(cpu)
                    if (mem := m.get("memory_percent", None)) is not None:
                        memory_timeline.append(mem)
                    if (threads := m.get("num_threads", None)) is not None:
                        thread_timeline.append(threads)

                # Calculate process running time
                running_time = 0
                if len(process_metrics) >= 2:
                    running_time = process_metrics[-1]["timestamp"] - process_metrics[0]["timestamp"]

                calculated_stats = {
                    "running_time": running_time,
                    "avg_cpu_percent": statistics.mean(
                        cpu_timeline
                    )
                    if cpu_timeline
                    else 0.0,
                    "avg_memory_percent": statistics.mean(
                        memory_timeline
                    )
                    if memory_timeline
                    else 0.0,
                    "max_num_threads": max(
                        thread_timeline
                    )
                    if thread_timeline
                    else 0,
                }

                process_info.update(calculated_stats)

                process_stats[pid] = process_info

        summary["processes"] = process_stats

    return summary

# Generalized Chart Creation Functions

def create_line_chart(data: Dict[str, List], title: str, x_title: str, y_title: str, 
                     div_id: str, colors: List[str] = None) -> str:
    """Create a generalized line chart.
    
    Args:
        data: Dictionary where keys are series names and values are data points
        title: Chart title
        x_title: X-axis title
        y_title: Y-axis title
        div_id: HTML div ID for the chart
        colors: Optional list of colors for the lines
        
    Returns:
        str: HTML div containing the Plotly chart
    """
    if not data:
        return f"<div>No data available for {title}</div>"
    
    if colors is None:
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    fig = go.Figure()
    
    for i, (series_name, values) in enumerate(data.items()):
        if values:  # Only add non-empty series
            x_values = list(range(len(values)))
            fig.add_trace(go.Scatter(
                x=x_values,
                y=values,
                mode='lines+markers',
                name=series_name,
                line=dict(color=colors[i % len(colors)], width=2)
            ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        hovermode='x',
        template='plotly_white'
    )
    
    return fig.to_html(include_plotlyjs=False, div_id=div_id)

def create_bar_chart(labels=None, values=None, data=None, title: str = '', 
                    x_title: str = '', y_title: str = '', div_id: str = '', 
                    color: str = '#1f77b4', orientation: str = 'v') -> str:
    """Create a generalized bar chart.
    
    Args:
        labels: List of labels for bars (optional if data dict is provided)
        values: List of values for bars (optional if data dict is provided)
        data: Dictionary with labels as keys and values as values (alternative to labels/values)
        title: Chart title
        x_title: X-axis title
        y_title: Y-axis title
        div_id: HTML div ID for the chart
        color: Bar color
        orientation: 'v' for vertical, 'h' for horizontal bars
        
    Returns:
        str: HTML div containing the Plotly chart
    """
    # Handle dictionary input
    if data is not None:
        if isinstance(data, dict):
            labels = list(data.keys())
            values = list(data.values())
        else:
            return f"<div>Invalid data format for {title}. Expected dictionary.</div>"
    
    # Validate input
    if not labels or not values:
        return f"<div>No data available for {title}</div>"
    
    if len(labels) != len(values):
        return f"<div>Labels and values length mismatch for {title}</div>"
    
    if orientation == 'v':
        fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color=color)])
        fig.update_layout(xaxis_tickangle=-45)
    else:
        fig = go.Figure(data=[go.Bar(x=values, y=labels, orientation='h', marker_color=color)])
    
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        template='plotly_white'
    )
    
    return fig.to_html(include_plotlyjs=False, div_id=div_id)

def create_pie_chart(labels=None, values=None, data=None, title: str = '', 
                    div_id: str = '', colors: List[str] = None) -> str:
    """Create a generalized pie chart.
    
    Args:
        labels: List of labels for pie slices (optional if data dict is provided)
        values: List of values for pie slices (optional if data dict is provided)
        data: Dictionary with labels as keys and values as values (alternative to labels/values)
        title: Chart title
        div_id: HTML div ID for the chart
        colors: Optional list of colors for the slices
        
    Returns:
        str: HTML div containing the Plotly chart
    """
    # Handle dictionary input
    if data is not None:
        if isinstance(data, dict):
            labels = list(data.keys())
            values = list(data.values())
        else:
            return f"<div>Invalid data format for {title}. Expected dictionary.</div>"
    
    # Validate input
    if not labels or not values:
        return f"<div>No data available for {title}</div>"
    
    if len(labels) != len(values):
        return f"<div>Labels and values length mismatch for {title}</div>"
    
    # Filter out zero values
    filtered_data = [(label, value) for label, value in zip(labels, values) if value > 0]
    if not filtered_data:
        return f"<div>No non-zero data available for {title}</div>"
    
    filtered_labels, filtered_values = zip(*filtered_data)
    
    fig = go.Figure(data=[go.Pie(
        labels=filtered_labels, 
        values=filtered_values,
        marker_colors=colors
    )])
    
    fig.update_layout(
        title=title,
        template='plotly_white'
    )
    
    return fig.to_html(include_plotlyjs=False, div_id=div_id)

def create_multi_series_line_chart(series_data: Dict[str, Dict[str, List]], 
                                  title: str, x_title: str, y_title: str, 
                                  div_id: str, colors: List[str] = None) -> str:
    """Create a line chart with multiple series, each with their own x and y values.
    
    Each series can have different x-axis values and different lengths, allowing
    for data points that start or end at arbitrary timepoints.
    
    Args:
        series_data: Dictionary where keys are series names and values are dictionaries
                    containing 'x' and 'y' keys with their respective data lists.
                    Format: {'series_name': {'x': [x_values], 'y': [y_values]}}
                    Alternatively, for backward compatibility, if values are just lists,
                    they will be treated as y-values with auto-generated x-values.
        title: Chart title
        x_title: X-axis title
        y_title: Y-axis title
        div_id: HTML div ID for the chart
        colors: Optional list of colors for the lines
        
    Returns:
        str: HTML div containing the Plotly chart
    """
    if not series_data:
        return f"<div>No data available for {title}</div>"
    
    if colors is None:
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    fig = go.Figure()
    
    for i, (series_name, data) in enumerate(series_data.items()):
        if data:
            # Handle backward compatibility: if data is a list, treat as y-values
            if isinstance(data, list):
                series_x = list(range(len(data)))
                series_y = data
            # Handle new format: data is a dict with 'x' and 'y' keys
            elif isinstance(data, dict) and 'x' in data and 'y' in data:
                x_values = data['x']
                y_values = data['y']
                
                if not x_values or not y_values:
                    continue
                    
                # Take minimum length to ensure x and y have same number of points
                min_length = min(len(x_values), len(y_values))
                if min_length > 0:
                    series_x = x_values[:min_length]
                    series_y = y_values[:min_length]
                else:
                    continue
            else:
                # Skip invalid data format
                continue
            
            if series_x and series_y:
                fig.add_trace(go.Scatter(
                    x=series_x,
                    y=series_y,
                    mode='lines+markers',
                    name=series_name,
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig.to_html(include_plotlyjs=False, div_id=div_id)

def generate_html_report(system_data: Dict, set_summaries: List[Dict], output_path: str = "report.html") -> str:
    """Generate a comprehensive HTML report with all charts.
    
    Args:
        run_data: Run-level monitoring data
        system_data: System-level monitoring data
        output_path: Path to save the HTML report
        
    Returns:
        str: Path to the generated HTML report
    """
    div_id_counter = 1
    # For each set summary
    for set_summary in set_summaries:

        # Get run summaries
        run_summaries = set_summary.get("runs", [])
        
        # For each run summary in a set
        for run_summary in run_summaries:
            # Init data structure
            process_names = []
            average_cpu_data = []
            average_memory_data = []
            cpu_series_data = {}

            # Extract average system metrics from summary data
            avg_system_cpu = run_summary.get("avg_system_cpu", [])
            avg_system_memory = run_summary.get("avg_system_memory", {})

            # Delete total from average system memory data
            if "total" in avg_system_memory:
                del avg_system_memory["total"]

            # Convert processes summary statistics into chart data
            # For each process info in run summary
            for pid, process_info in run_summary.get("processes", {}).items():
                process_names.append(f"{process_info.get('name', None)} {pid}")
                average_cpu_data.append(process_info.get("avg_cpu_percent", 0.0))
                average_memory_data.append(process_info.get("avg_memory_percent", 0.0))
                
                # Transform process CPU usage over time into time series data for visualization
                process_step_timeline = []
                process_cpu_timeline = []
                for m in process_info.get("metrics", []):
                    if (step := m.get("step", None)) is not None:
                        process_step_timeline.append(step)
                    if (cpu := m.get("cpu_percent", None)) is not None:
                        process_cpu_timeline.append(cpu)
                cpu_series_data[pid] = {
                    "x": process_step_timeline,
                    "y": process_cpu_timeline
                }
                
                # Create charts
                run_summary.update({"charts": {
                    'system_cpu_chart': create_bar_chart(
                        labels=[f"{i}" for i in range(1, len(avg_system_cpu) + 1)],
                        values=avg_system_cpu,
                        title='Average System CPU Usage (per-core)',
                        x_title='CPU Core',
                        y_title='CPU Usage (%)',
                        div_id=f'system-cpu-chart-{div_id_counter}',
                        color='#1f77b4'
                    ),
                    'system_memory_chart': create_pie_chart(
                        data=avg_system_memory,
                        title='Average System Memory Usage',
                        div_id=f'system-memory-chart-{div_id_counter}',
                    ),
                    'process_cpu_chart': create_bar_chart(
                        labels=process_names,
                        values=average_cpu_data,
                        title='Average CPU Usage by Process',
                        x_title='Process (PID)',
                        y_title='CPU Usage (%)',
                        div_id=f'process-cpu-chart-{div_id_counter}',
                        color='#ff7f0e'
                    ),
                    'process_memory_chart': create_bar_chart(
                        labels=process_names,
                        values=average_memory_data,
                        title='Average Memory Usage by Process',
                        x_title='Process (PID)',
                        y_title='Memory Usage (%)',
                        div_id=f'process-memory-chart-{div_id_counter}',
                        color='#2ca02c'
                    ),
                    'process_timeline_chart': create_multi_series_line_chart(
                        series_data=cpu_series_data,
                        title='Process CPU Usage Timeline',
                        x_title='Timestamp',
                        y_title='CPU Usage (%)',
                        div_id=f'process-timeline-chart-{div_id_counter}'
                    )}
                })

                div_id_counter += 1
    
    # Prepare template context
    context = {
        'title': 'GeoBench Performance Report',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'system_data': system_data,
        'set_summaries': set_summaries,
    }
    
    # Load and render template
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('report_template.html')
    
    html_content = template.render(context)
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_path

#%%

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python report.py <step_result_path> [system_result_path] [output_path]")
        print("Example: python report.py test/short-result/step-result.json test/short-result/system-result.json report.html")
        sys.exit(1)
    
    report_dir_path = sys.argv[1]
    output_path = sys.argv[2]

    run_report_path = []
    system_report_path = None
    # Iterate through sub directory
    for root, dirs, files in os.walk(report_dir_path):
        for filename in files:
            if filename == "result.json":
                # Check if it is in root directory
                if root == report_dir_path:
                    system_report_path = os.path.join(root, filename)
                else:
                    run_report_path.append(os.path.join(root, filename))

    if (system_report_path := os.path.join(report_dir_path, "result.json")):
        with open(system_report_path, 'r') as f:
            system_data = json.load(f)

    # Iterate for directory inside report_dir_path (one-level)
    set_summaries = []
    for set_items in os.listdir(report_dir_path):
        if os.path.isdir(os.path.join(report_dir_path, set_items)):
            set_summary = {
                "set": 0,
                "arguments": {},
                "runs": []
            }

            sorted_listdir = sorted(os.listdir(os.path.join(report_dir_path, set_items)))
            for run_items in sorted_listdir:
                if os.path.isdir(os.path.join(report_dir_path, set_items, run_items)):
                    if (run_path := os.path.join(report_dir_path, set_items, run_items, "result.json")):
                        with open(run_path, 'r') as f:
                            run_data = json.load(f)
                            set_summary["set"] = run_data.get("set", 0)
                            set_summary["arguments"] = run_data.get("arguments", {})
                            summary = calculate_run_summary(run_data)
                            set_summary["runs"].append(summary)
                            
            runs_len = len(set_summary["runs"])
            set_summary["total"] = runs_len
            set_summary["success"] = (sum(1 for run in set_summary["runs"] if run["success"]) / runs_len) if runs_len > 0 else 0
            set_summaries.append(set_summary)

    generate_html_report(system_data, set_summaries, output_path)

#%%