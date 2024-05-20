use csv::Reader;
use linregress::{FormulaRegressionBuilder, RegressionDataBuilder};
use serde::Deserialize;
use std::error::Error;
use std::fs::File;
use std::io::BufReader;

#[derive(Debug, Deserialize)]
struct VMData {
    vm_type: String,
    idle: f64,
    usage_10: f64,
    usage_50: f64,
    usage_100: f64,
}

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

fn main() -> Result<(), Box<dyn Error>> {
    let vm_type = "a1.large"; // Specify the VM type
    let vm_data = read_csv("vm_data.csv", vm_type)?;

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
    let data = RegressionDataBuilder::new()
        .build_from(raw_data)?;

    // Perform the regression
    let formula = "Y ~ X";
    let model = FormulaRegressionBuilder::new()
        .data(&data)
        .formula(formula)
        .fit()?;

    // Output the regression parameters
    println!("Regression model for VM type '{}':", vm_type);
    let parameters: Vec<_> = model.iter_parameter_pairs().collect();
    let pvalues: Vec<_> = model.iter_p_value_pairs().collect();

    let new_data = vec![
        ("X", vec![5.0, 10.0])
    ];      
    let data = model.predict(new_data)?;
    println!("{}", data[0]);
    for (name, value) in parameters {
        println!("{}: {}", name, value);
    }
    for (name, value) in pvalues {
        println!("{}: {}", name, value);
    }
    Ok(())
}