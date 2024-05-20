use axum::{
    extract::State, http::StatusCode, routing::get, Router
};
use prometheus::{register_gauge, Encoder, Gauge, TextEncoder};
use sysinfo::System;
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
}

// Define the structure for a row in the CSV
#[derive(Debug, Deserialize)]
struct VMData {
    vm_type: String,
    idle: f64,
    usage_10: f64,
    usage_25: f64,
    usage_50: f64,
    usage_100: f64,
}

impl VMData {
    fn energy_for_usage(&self, usage: f64) -> f64 {
        match usage {
            u if u <= 0.0 => self.idle,
            u if u <= 10.0 => self.usage_10,
            u if u <= 25.0 => self.usage_25,
            u if u <= 50.0 => self.usage_50,
            u if u <= 100.0 => self.usage_100,
            _ => self.usage_100, // Any value above 100% is treated as 100%
        }
    }
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
    let power_gauge = register_gauge!("power_consumption", "Estimated power consumption").unwrap();

    // Specify the VM type
    let vm_type = "vm1";

    // Read the CSV file and find the row for the specified VM type
    let vm_data = read_csv("vm_data.csv", vm_type).unwrap();

    let app_state = Arc::new(Mutex::new(AppState{cpu_usage: 0.0, power_consumption:0.0, power_gauge: power_gauge.clone()}));

    let mut sys = System::new();

    let cloned_state = app_state.clone();

    // Spawn a task to update the CPU usage periodically
    {
        tokio::spawn(async move {
            loop {
                sys.refresh_cpu();
                let cpu_usage_value = sys.global_cpu_info().cpu_usage() as f64;
                let power_consumption_value = vm_data.energy_for_usage(cpu_usage_value);
                let mut state = app_state.lock().unwrap();
                state.cpu_usage = cpu_usage_value;
                state.power_consumption = power_consumption_value;
                state.power_gauge.set(power_consumption_value);
                print!("{}%\n", cpu_usage_value);
                std::thread::sleep(sysinfo::MINIMUM_CPU_UPDATE_INTERVAL);
            }
        });
    }
    
    let app = Router::new()
        .route("/metrics", get(metrics_handler))
        .with_state(cloned_state);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:9000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn metrics_handler(State(_): State<Arc<Mutex<AppState>>>) -> Result<String, (StatusCode, String)> {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    encoder.encode(&metric_families, &mut buffer).unwrap();
    let data = String::from_utf8(buffer).unwrap();
    return Ok(data);
}