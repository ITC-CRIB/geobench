import argparse
import ansible_runner
import os

class CommandLineTool:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Toolkit for benchmarking the geospatial processing workload")
        self.parser.add_argument('-i', '--inventory', type=str, help='Inventory file', default='inventory.yml')
        self.subparsers = self.parser.add_subparsers(dest="command")

        # Create subparsers for "test" command
        self.test_parser = self.subparsers.add_parser("test", help='Manage the benchmarking tests')
        self.run_subparsers = self.test_parser.add_subparsers(dest="subcommand")
        # Subparser for the 'test run <scenario> <id>' subcommand
        self.run_parser = self.run_subparsers.add_parser('run', help='Run the benchmarking test. test run <scenario_path> <id>')
        self.run_parser.add_argument('path', type=str, help='Path of scenario directory in local computer')
        self.run_parser.add_argument('id', type=str, help='The scenario id')
        self.run_parser.add_argument('-r', '--repeat', type=int, help='The amount of execution repeat', default=10)
        self.run_parser.add_argument('-c', '--converge', type=int, help='The number of converging percentage (in percent)', default=10)
        # Subparser for the 'test list' subcommand
        self.run_parser = self.run_subparsers.add_parser('list', help='List all benchmarking scenario')
        # Subparser for the 'test remove <id>' subcommand
        self.run_parser = self.run_subparsers.add_parser('remove', help='Delete benchmarking scenario given the scenario id')
        self.run_parser.add_argument('id', type=str, help='The scenario id')
        # Subparser for the 'test save <id>' subcommand
        self.run_parser = self.run_subparsers.add_parser('save', help='Save benchmarking scenario to a specific local folder given the scenario id')
        self.run_parser.add_argument('id', type=str, help='The scenario id')
        # Subparser for the 'test save <id>' subcommand
        self.run_parser = self.run_subparsers.add_parser('inspect', help='Show benchmarking report result given the scenario id')
        self.run_parser.add_argument('id', type=str, help='The scenario id')
        # Subparser for the 'test display <id>' subcommand
        self.run_parser = self.run_subparsers.add_parser('display', help='Open Grafana dashboard given the scenario id')
        self.run_parser.add_argument('id', type=str, help='The scenario id')

        # Create subparsers for "snapshot" command
        self.snapshot_parser = self.subparsers.add_parser("snapshot", help='Manage snapshot')
        self.snapshot_subparsers = self.snapshot_parser.add_subparsers(dest="subsubcommand")
        # Subparser for the 'snapshot list' subcommand
        self.snapshot_parser = self.snapshot_subparsers.add_parser('list', help='List all snapshots')
        # Subparser for the 'snapshot remove <id>' subcommand
        self.snapshot_parser = self.snapshot_subparsers.add_parser('remove', help='Delete snapshot given the snapshot id')
        self.snapshot_parser.add_argument('id', type=str, help='The snapshot id')
        # Subparser for the 'snapshot save <id>' subcommand
        self.snapshot_parser = self.snapshot_subparsers.add_parser('save', help='Save snapshot to a specific local folder given the scenario id')
        self.snapshot_parser.add_argument('id', type=str, help='The snapshot id')
        # Subparser for the 'snapshot inspect <id>' subcommand
        self.snapshot_parser = self.snapshot_subparsers.add_parser('inspect', help='Show snapshot given the scenario id')
        self.snapshot_parser.add_argument('id', type=str, help='The snapshot id')
        

    def run(self):
        args = self.parser.parse_args()
        inventory_path = os.path.abspath(args.inventory)
        
        if args.command == 'test':
            self.handle_test(args, inventory_path)
        elif args.command == 'snapshot':
            self.handle_snapshot(args, inventory_path)
        else:
            self.parser.print_help()

    def handle_test(self, args, inventory_path):
        if args.subcommand == "run":
            # Running the playbook
            r = ansible_runner.interface.run(
                private_data_dir = 'ansible' ,
                playbook='run-scenario.yml',
                #extravars={'src_dir': src_dir, 'dest_dir': dest_dir},
                inventory=inventory_path
            )
            print(args.subcommand)
            #print(f"{args.greet}, {args.name}!")
    
    def handle_snapshot(self, args, inventory_path):
        print(args.subcommand)
        #print(f"{args.greet}, {args.name}!")


if __name__ == "__main__":
    tool = CommandLineTool()
    tool.run()
