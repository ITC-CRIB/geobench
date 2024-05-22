from prometheus_api_client import PrometheusConnect
import pandas as pd
import plotly.express as px
from jinja2 import Template
import datetime

# Initialize Prometheus client
prom = PrometheusConnect(url="http://3.66.166.68:9090", disable_ssl=True)

# Define the time range for the query
end_time = datetime.datetime.now()
start_time = end_time - datetime.timedelta(hours=1)

# Prometheus queries for CPU, memory, and energy consumption
queries = {
    'CPU Utilization': 'avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) by (node)',
    'Memory Usage': 'avg(node_memory_Active_bytes / node_memory_MemTotal_bytes) by (node)',
    'Energy Consumption': 'power_consumption{node=~"master-0|worker-0|worker-1"}'
}

# Fetch data
def query_prometheus(query):
    return prom.custom_query_range(
        query=query, 
        start_time=start_time, 
        end_time=end_time, 
        step='60s'
    )

def process_data(data):
    processed_data = {}
    for metric_name, result in data.items():
        for metric in result:
            node = metric['metric']['node']
            timestamps, values = zip(*metric['values'])
            df = pd.DataFrame({'timestamp': timestamps, metric_name: values})
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            if node not in processed_data:
                processed_data[node] = {metric_name: df}
            else:
                processed_data[node][metric_name] = df
    return processed_data

def generate_plots(data):
    plots = []
    for node, metrics in data.items():
        for metric_name, df in metrics.items():
            fig = px.line(df, x='timestamp', y=metric_name, title=f'{metric_name} for {node}')
            plot_name = f'{node}_{metric_name}.html'
            plot_path = f'reports/{plot_name}'
            fig.write_html(plot_path)
            plots.append(plot_name)
    return plots

data = {name: query_prometheus(query) for name, query in queries.items()}
processed_data = process_data(data)
plots = generate_plots(processed_data)

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prometheus Metrics Report</title>
</head>
<body>
    <h1>Prometheus Metrics Visualization</h1>
    {% for plot in plots %}
    <div>
        <h2>{{ plot.split('_')[0] }}</h2>
        <iframe src="{{ plot }}" width="100%" height="600"></iframe>
    </div>
    {% endfor %}
</body>
</html>
"""

template = Template(html_template)
html_content = template.render(plots=plots)

with open(f'reports/metrics_report.html', 'w') as f:
    f.write(html_content)