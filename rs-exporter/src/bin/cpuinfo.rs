use std::{thread, time::Duration};

use sysinfo::System;

fn main(){
    let mut sys = System::new();

    loop {
        sys.refresh_cpu();
        let cpu_usage_value = sys.global_cpu_info().cpu_usage() as f64;
        println!("CPU Usage: {}", cpu_usage_value);
        for cpu in sys.cpus() {
            println!("- CPU {}%", cpu.cpu_usage());
        }
        thread::sleep(Duration::from_millis(1000));
    }
}