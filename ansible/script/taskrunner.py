import subprocess
import time
import csv
import argparse

def invoke_process(program, params):
    start_time = time.time() 
    # Invoke the process
    subprocess.run([program] + params)
    end_time = time.time()
    exec_time = end_time - start_time
    return start_time, end_time, exec_time

def write_to_csv(data):
    with open('process_times.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Invoke a process and measure start and end time.')
    parser.add_argument('name', help='Name of the scenario')
    parser.add_argument('repetition', type=int, help='Amount of repetitions', default=1)
    parser.add_argument('program', help='Name of the program to invoke')
    parser.add_argument('params', nargs=argparse.REMAINDER, help='Parameters for the program')
    args = parser.parse_args()

    name = args.name
    repetition = args.repetition
    program = args.program
    params = args.params

    for i in range(0, repetition):
        start_time, end_time, exec_time = invoke_process(program, params)

        # Convert times to human-readable format
        start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
        end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))

        # Write data to CSV file
        data = [name, start_time * 1000, end_time * 1000, exec_time, start_time_str, end_time_str]
        write_to_csv(data)

        # print(f"Process '{name}' started at: {start_time_str}")
        # print(f"Process '{name}' ended at: {end_time_str}")
