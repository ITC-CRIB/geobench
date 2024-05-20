use axum::{
    extract::State, http::StatusCode, routing::get, Router
};
use linregress::{FormulaRegressionBuilder, RegressionDataBuilder};
use prometheus::{register_gauge, Encoder, Gauge, TextEncoder};
use sysinfo::System;
use std::env;
use std::sync::{Arc, Mutex};

use csv::Reader;
use serde::Deserialize;
use std::error::Error;
use std::fs::File;
use std::io::BufReader;

struct AppState {
    cpu_usage: f64,
    power_consumption: f64,
    power_gauge: Gauge,
    cpu_gauge: Gauge,
}

// Define the structure for a row in the CSV
#[derive(Debug, Deserialize)]
struct VMData {
    vm_type: String,
    idle: f64,
    usage_10: f64,
    usage_50: f64,
    usage_100: f64,
}

impl VMData {
    // fn energy_for_usage(&self, usage: f64) -> f64 {
    //     match usage {
    //         u if u <= 0.0 => self.idle,
    //         u if u <= 10.0 => self.usage_10,
    //         u if u <= 50.0 => self.usage_50,
    //         u if u <= 100.0 => self.usage_100,
    //         _ => self.usage_100, // Any value above 100% is treated as 100%
    //     }
    // }
}

// Function to read the CSV file and find the row for the specified VM type
fn read_csv(filename: &str, vm_type: &str) -> Result<VMData, Box<dyn Error>> {
    let file = File::open(filename)?;
    let mut rdr = Reader::from_reader(BufReader::new(file));
    for result in rdr.deserialize() {
        let record: VMData = result?;
        if record.vm_type == vm_type {
            return Ok(record);
        }
    }
    Err(From::from(format!("VM type {} not found", vm_type)))
}


#[tokio::main]
async fn main() {
    // Read the app port from the environment variable
    let app_port = env::var("APP_PORT").unwrap_or("0.0.0.0:9100".to_owned());
    // Read the VM type from the environment variable
    let vm_type = env::var("VM_TYPE").unwrap_or("a1.large".to_owned());

    // Init the metrics registry
    let mut sys = System::new();
    let power_gauge = register_gauge!("power_consumption", "Estimated power consumption").unwrap();
    let cpu_gauge = register_gauge!("cpu_usage", "Average CPU utilization for all cores").unwrap();

    // Read the CSV file and find the row for the specified VM type
    let vm_data = read_csv("vm_data.csv", &vm_type).unwrap();
    // Create the data for regression
    let x_values = vec![0.0, 10.0, 50.0, 100.0];
    let y_values = vec![
        vm_data.idle,
        vm_data.usage_10,
        vm_data.usage_50,
        vm_data.usage_100,
    ];
    let raw_data = vec![("Y", y_values), ("X", x_values)];
    // Prepare the data for the regression model
    let regression_data = RegressionDataBuilder::new()
        .build_from(raw_data).unwrap();
    // Perform the regression
    let formula = "Y ~ X";
    let model = FormulaRegressionBuilder::new()
        .data(&regression_data)
        .formula(formula)
        .fit().unwrap();

    // Define the shared app state
    let app_state = Arc::new(Mutex::new(
        AppState{
            cpu_usage: 0.0, 
            power_consumption:0.0, 
            power_gauge: power_gauge.clone(),
            cpu_gauge: cpu_gauge.clone(),
        }));
    // Clone the app state to pass to the async task
    let cloned_state = app_state.clone();

    // Spawn a task to update the CPU usage periodically
    {
        tokio::spawn(async move {
            loop {
                // Refresh the CPU usage reading
                sys.refresh_cpu();
                let cpu_usage_value = sys.global_cpu_info().cpu_usage() as f64;
                // let power_consumption_value = vm_data.energy_for_usage(cpu_usage_value);
                let new_data = vec![
                    ("X", vec![cpu_usage_value])
                ];
                // Perform the regression to estimate the power consumption
                let power_consumption_value = model.predict(new_data).unwrap()[0];
                // Update the app state
                let mut state = app_state.lock().unwrap();
                state.cpu_usage = cpu_usage_value;
                state.power_consumption = power_consumption_value;
                state.power_gauge.set(power_consumption_value);
                state.cpu_gauge.set(cpu_usage_value);
                //print!("{}%\n", cpu_usage_value);
                std::thread::sleep(sysinfo::MINIMUM_CPU_UPDATE_INTERVAL);
            }
        });
    }
    // Router to handle the metrics requests
    let app = Router::new()
        .route("/metrics", get(metrics_handler))
        .with_state(cloned_state);

    // Start the server
    println!("Daemon is running on {}", &app_port);
    let listener = tokio::net::TcpListener::bind(&app_port).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn metrics_handler(State(_): State<Arc<Mutex<AppState>>>) -> Result<String, (StatusCode, String)> {
    // Gather the metrics
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    // Encode the metrics
    encoder.encode(&metric_families, &mut buffer).unwrap();
    let data = String::from_utf8(buffer).unwrap();
    // Return the metrics
    return Ok(data);
}