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
        "avg_system_cpu": [],
        "avg_system_memory": {},
        "process": {}
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

    process_stats = {}
    if run_result["processes"]:
        for pid, process_info in run_result["processes"].items():
            process_metrics = process_info["metrics"]
            del process_info["metrics"]
            process_stats[pid] = {
                **process_info,
                "avg_cpu_percent": statistics.mean(
                    [m["cpu_percent"] for m in process_metrics if m["cpu_percent"] is not None]
                )
                if process_metrics
                else 0.0,
                "avg_memory_percent": statistics.mean(
                    [m["memory_percent"] for m in process_metrics if m["memory_percent"] is not None]
                )
                if process_metrics  
                else 0.0,
                "max_num_threads": max(
                    [m["num_threads"] for m in process_metrics if m["num_threads"] is not None]
                )
                if process_metrics
                else 0,
            }
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

def create_bar_chart(labels: List[str], values: List[float], title: str, 
                    x_title: str, y_title: str, div_id: str, 
                    color: str = '#1f77b4', orientation: str = 'v') -> str:
    """Create a generalized bar chart.
    
    Args:
        labels: List of labels for bars
        values: List of values for bars
        title: Chart title
        x_title: X-axis title
        y_title: Y-axis title
        div_id: HTML div ID for the chart
        color: Bar color
        orientation: 'v' for vertical, 'h' for horizontal bars
        
    Returns:
        str: HTML div containing the Plotly chart
    """
    if not labels or not values:
        return f"<div>No data available for {title}</div>"
    
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

def create_pie_chart(labels: List[str], values: List[float], title: str, 
                    div_id: str, colors: List[str] = None) -> str:
    """Create a generalized pie chart.
    
    Args:
        labels: List of labels for pie slices
        values: List of values for pie slices
        title: Chart title
        div_id: HTML div ID for the chart
        colors: Optional list of colors for the slices
        
    Returns:
        str: HTML div containing the Plotly chart
    """
    if not labels or not values:
        return f"<div>No data available for {title}</div>"
    
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

def create_multi_series_line_chart(x_values: List, series_data: Dict[str, List], 
                                  title: str, x_title: str, y_title: str, 
                                  div_id: str, colors: List[str] = None) -> str:
    """Create a line chart with multiple series sharing the same x-axis.
    
    Series with different lengths are supported. Each series will be plotted
    using the minimum of its length and the x_values length.
    
    Args:
        x_values: List of x-axis values (timestamps, steps, etc.)
        series_data: Dictionary where keys are series names and values are y-values.
                    Series can have different lengths.
        title: Chart title
        x_title: X-axis title
        y_title: Y-axis title
        div_id: HTML div ID for the chart
        colors: Optional list of colors for the lines
        
    Returns:
        str: HTML div containing the Plotly chart
    """
    if not series_data or not x_values:
        return f"<div>No data available for {title}</div>"
    
    if colors is None:
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    fig = go.Figure()
    
    for i, (series_name, y_values) in enumerate(series_data.items()):
        if y_values:
            # Handle series with different lengths by taking the minimum of available data
            min_length = min(len(x_values), len(y_values))
            if min_length > 0:
                series_x = x_values[:min_length]
                series_y = y_values[:min_length]
                
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
        hovermode='x',
        template='plotly_white'
    )
    
    return fig.to_html(include_plotlyjs=False, div_id=div_id)

# Specific Chart Functions Using Generalized Functions

def create_system_cpu_chart(system_data: List[Dict]) -> str:
    """Create a line chart showing system CPU usage over time."""
    if not system_data:
        return "<div>No system data available</div>"
    
    cpu_percent = []
    for data in system_data:
        if isinstance(data, dict) and 'cpu_percent' in data:
            cpu_val = data['cpu_percent']
            if isinstance(cpu_val, list):
                cpu_percent.append(statistics.mean([c for c in cpu_val if c is not None]))
            else:
                cpu_percent.append(cpu_val if cpu_val is not None else 0)
        else:
            cpu_percent.append(0)
    
    data_dict = {'System CPU Usage': cpu_percent}
    return create_line_chart(
        data=data_dict,
        title='System CPU Usage Over Time',
        x_title='Time Steps',
        y_title='CPU Usage (%)',
        div_id='system-cpu-chart'
    )

def create_system_memory_chart(system_data: List[Dict]) -> str:
    """Create a line chart showing system memory usage over time."""
    if not system_data:
        return "<div>No system data available</div>"
    
    memory_data = {}
    
    # Extract memory types
    for data in system_data:
        memory_usage = data.get('memory_usage', {})
        for mem_type, value in memory_usage.items():
            if mem_type not in memory_data:
                memory_data[mem_type] = []
            memory_data[mem_type].append(value if value is not None else 0)
    
    # If no memory_usage field, try to extract from memory field
    if not memory_data:
        for data in system_data:
            memory_info = data.get('memory', {})
            if memory_info:
                for mem_type, value in memory_info.items():
                    if mem_type not in memory_data:
                        memory_data[mem_type] = []
                    memory_data[mem_type].append(value if value is not None else 0)
    
    if not memory_data:
        return "<div>No memory data available</div>"
    
    # Rename keys for better display
    display_data = {f'Memory {k}': v for k, v in memory_data.items()}
    
    return create_line_chart(
        data=display_data,
        title='System Memory Usage Over Time',
        x_title='Time Steps',
        y_title='Memory Usage (%)',
        div_id='system-memory-chart'
    )

def create_process_cpu_chart(processes_data: Dict) -> str:
    """Create a bar chart showing average CPU usage per process."""
    if not processes_data:
        return "<div>No process data available</div>"
    
    process_names = []
    cpu_averages = []
    
    for pid, process_info in processes_data.items():
        metrics = process_info.get('metrics', [])
        if metrics:
            cpu_values = [m['cpu_percent'] for m in metrics if m.get('cpu_percent') is not None]
            avg_cpu = statistics.mean(cpu_values) if cpu_values else 0
            process_names.append(f"{process_info.get('name', 'Unknown')} ({pid})")
            cpu_averages.append(avg_cpu)
    
    return create_bar_chart(
        labels=process_names,
        values=cpu_averages,
        title='Average CPU Usage by Process',
        x_title='Process (PID)',
        y_title='CPU Usage (%)',
        div_id='process-cpu-chart',
        color='#ff7f0e'
    )

def create_process_memory_chart(processes_data: Dict) -> str:
    """Create a bar chart showing average memory usage per process."""
    if not processes_data:
        return "<div>No process data available</div>"
    
    process_names = []
    memory_averages = []
    
    for pid, process_info in processes_data.items():
        metrics = process_info.get('metrics', [])
        if metrics:
            memory_values = [m['memory_percent'] for m in metrics if m.get('memory_percent') is not None]
            avg_memory = statistics.mean(memory_values) if memory_values else 0
            process_names.append(f"{process_info.get('name', 'Unknown')} ({pid})")
            memory_averages.append(avg_memory)
    
    return create_bar_chart(
        labels=process_names,
        values=memory_averages,
        title='Average Memory Usage by Process',
        x_title='Process (PID)',
        y_title='Memory Usage (%)',
        div_id='process-memory-chart',
        color='#2ca02c'
    )

def create_process_timeline_chart(processes_data: Dict) -> str:
    """Create a timeline chart showing when processes were active."""
    if not processes_data:
        return "<div>No process data available</div>"
    
    # Find common timestamps
    all_timestamps = set()
    for process_info in processes_data.values():
        metrics = process_info.get('metrics', [])
        for metric in metrics:
            all_timestamps.add(metric.get('timestamp', 0))
    
    if not all_timestamps:
        return "<div>No timestamp data available</div>"
    
    timestamps = sorted(list(all_timestamps))
    series_data = {}
    
    for pid, process_info in processes_data.items():
        metrics = process_info.get('metrics', [])
        if metrics:
            # Create a mapping of timestamp to CPU value
            cpu_by_timestamp = {m['timestamp']: m.get('cpu_percent', 0) for m in metrics}
            
            # Fill in values for all timestamps
            cpu_values = [cpu_by_timestamp.get(ts, 0) for ts in timestamps]
            series_name = f"{process_info.get('name', 'Unknown')} ({pid})"
            series_data[series_name] = cpu_values
    
    return create_multi_series_line_chart(
        x_values=timestamps,
        series_data=series_data,
        title='Process CPU Usage Timeline',
        x_title='Timestamp',
        y_title='CPU Usage (%)',
        div_id='process-timeline-chart'
    )

def create_system_overview_chart(system_data: Dict) -> str:
    """Create a dashboard-style overview of system information."""
    if not system_data or 'system' not in system_data:
        return "<div>No system overview data available</div>"
    
    system_info = system_data['system']
    
    # Create subplots for different metrics
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('CPU Cores', 'Memory Distribution', 'Disk Usage', 'System Load'),
        specs=[[{"type": "indicator"}, {"type": "pie"}],
               [{"type": "pie"}, {"type": "indicator"}]]
    )
    
    # CPU cores indicator
    cpu_info = system_info.get('cpu', {})
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=cpu_info.get('logical_count', 0),
            title={"text": "CPU Cores"},
            number={'suffix': " cores"}
        ),
        row=1, col=1
    )
    
    # Memory pie chart
    memory_info = system_info.get('memory', {})
    if memory_info:
        used = memory_info.get('used', 0)
        available = memory_info.get('available', 0)
        if used > 0 or available > 0:
            fig.add_trace(
                go.Pie(
                    labels=['Used', 'Available'],
                    values=[used, available],
                    name="Memory"
                ),
                row=1, col=2
            )
    
    # Disk usage pie chart
    disk_info = system_info.get('disk', [])
    if disk_info:
        disk = disk_info[0]  # Use first disk
        used = disk.get('used', 0)
        free = disk.get('free', 0)
        if used > 0 or free > 0:
            fig.add_trace(
                go.Pie(
                    labels=['Used', 'Free'],
                    values=[used, free],
                    name="Disk"
                ),
                row=2, col=1
            )
    
    # System load indicator
    baseline = system_data.get('baseline', {})
    cpu_load = baseline.get('avg_cpu_percent', 0)
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=cpu_load,
            title={'text': "Avg CPU Load"},
            gauge={'axis': {'range': [None, 100]},
                   'bar': {'color': "darkblue"},
                   'steps': [{'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 80], 'color': "yellow"},
                            {'range': [80, 100], 'color': "red"}],
                   'threshold': {'line': {'color': "red", 'width': 4},
                               'thickness': 0.75, 'value': 90}}
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        title='System Overview',
        height=600,
        template='plotly_white'
    )
    
    return fig.to_html(include_plotlyjs=False, div_id="system-overview-chart")

# Additional utility functions for creating charts from monitoring data

def create_memory_distribution_pie_chart(memory_info: Dict) -> str:
    """Create a standalone pie chart for memory distribution."""
    if not memory_info:
        return "<div>No memory information available</div>"
    
    labels = []
    values = []
    
    for key, value in memory_info.items():
        if isinstance(value, (int, float)) and value > 0:
            labels.append(key.capitalize())
            values.append(value)
    
    return create_pie_chart(
        labels=labels,
        values=values,
        title='Memory Distribution',
        div_id='memory-distribution-chart'
    )

def create_disk_usage_pie_chart(disk_info: List[Dict]) -> str:
    """Create a standalone pie chart for disk usage."""
    if not disk_info:
        return "<div>No disk information available</div>"
    
    # Use first disk or combine all disks
    disk = disk_info[0] if disk_info else {}
    
    labels = ['Used', 'Free']
    values = [disk.get('used', 0), disk.get('free', 0)]
    
    return create_pie_chart(
        labels=labels,
        values=values,
        title='Disk Usage Distribution',
        div_id='disk-usage-chart',
        colors=['#ff6b6b', '#4ecdc4']
    )

def create_process_threads_chart(processes_data: Dict) -> str:
    """Create a bar chart showing maximum threads per process."""
    if not processes_data:
        return "<div>No process data available</div>"
    
    process_names = []
    max_threads = []
    
    for pid, process_info in processes_data.items():
        metrics = process_info.get('metrics', [])
        if metrics:
            thread_counts = [m['num_threads'] for m in metrics if m.get('num_threads') is not None]
            max_thread_count = max(thread_counts) if thread_counts else 0
            process_names.append(f"{process_info.get('name', 'Unknown')} ({pid})")
            max_threads.append(max_thread_count)
    
    return create_bar_chart(
        labels=process_names,
        values=max_threads,
        title='Maximum Threads by Process',
        x_title='Process (PID)',
        y_title='Thread Count',
        div_id='process-threads-chart',
        color='#9467bd'
    )

def generate_html_report(system_data: Dict, run_data: List[Dict], output_path: str = "report.html") -> str:
    """Generate a comprehensive HTML report with all charts.
    
    Args:
        run_data: Run-level monitoring data
        system_data: System-level monitoring data
        output_path: Path to save the HTML report
        
    Returns:
        str: Path to the generated HTML report
    """
    # Generate all charts
    # For step data, we don't have system-level metrics in the same structure
    # Calculate summary statistics
    
    for run in run_data:

        process_names = []
        average_cpu_data = []
        average_memory_data = []
        cpu_series_data = {}

        step_id = [m["step"] for m in run["system"] if "step" in m]

        for pid, process_info in run["processes"].items():
            process_metrics = process_info["metrics"]
            process_name = "{} {}".format(process_info.get("name", None), pid)
            
            cpu_timeline = [m["cpu_percent"] for m in process_metrics if m["cpu_percent"] is not None]
            memory_timeline = [m["memory_percent"] for m in process_metrics if m["memory_percent"] is not None]
            thread_timeline = [m["num_threads"] for m in process_metrics if m["num_threads"] is not None]

            average_cpu = statistics.mean(
                cpu_timeline
            ) if process_metrics else 0.0

            average_memory = statistics.mean(
                memory_timeline
            ) if process_metrics else 0.0

            max_thread = max(thread_timeline) if thread_timeline else 0

            process_info.update({
                'avg_cpu_percent': average_cpu,
                'avg_memory_percent': average_memory,
                'max_num_threads': max_thread
            })

            # Append to list for chart generation
            average_cpu_data.append(average_cpu)
            average_memory_data.append(average_memory)
            process_names.append(process_name)
            cpu_series_data[process_name] = cpu_timeline

        run.update({"charts": {
            'process_cpu_chart': create_bar_chart(
                labels=process_names,
                values=average_cpu_data,
                title='Average CPU Usage by Process',
                x_title='Process (PID)',
                y_title='CPU Usage (%)',
                div_id='process-cpu-chart',
                color='#ff7f0e'
            ),
            'process_memory_chart': create_bar_chart(
                labels=process_names,
                values=average_memory_data,
                title='Average Memory Usage by Process',
                x_title='Process (PID)',
                y_title='Memory Usage (%)',
                div_id='process-memory-chart',
                color='#2ca02c'
            ),
            'process_timeline_chart': create_multi_series_line_chart(
                x_values=step_id,
                series_data=cpu_series_data,
                title='Process CPU Usage Timeline',
                x_title='Timestamp',
                y_title='CPU Usage (%)',
                div_id='process-timeline-chart'
            )}
        })
    # So we'll focus on process data and use system_data for system charts
    system_charts = {
        'system_cpu_chart': create_system_cpu_chart([]),  # No step-level system data
        'system_memory_chart': create_system_memory_chart([]),  # No step-level system data
        'system_overview_chart': create_system_overview_chart(system_data),
    }
    
    # Prepare template context
    context = {
        'title': 'GeoBench Performance Report',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'system_data': system_data,
        'run_data': run_data,
        'charts': system_charts
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

    step_report_path = []
    system_report_path = None
    # Iterate through sub directory
    for root, dirs, files in os.walk(report_dir_path):
        for filename in files:
            if filename == "result.json":
                # Check if it is in root directory
                if root == report_dir_path:
                    system_report_path = os.path.join(root, filename)
                else:
                    step_report_path.append(os.path.join(root, filename))

    step_report = []
    for path in step_report_path:
        with open(path, 'r') as f:
            step_data = json.load(f)
            step_report.append(step_data)

    with open(system_report_path, 'r') as f:
        system_data = json.load(f)

    generate_html_report(system_data, step_report, output_path)

#%%