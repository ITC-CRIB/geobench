"""An AWS Python Pulumi program"""

import pulumi
from pulumi_aws import lightsail
from pulumi import Output
import yaml

# Configuration
# instance_size = "small_ipv6_3_0"  # 2 GB RAM instance type
master_instance_size = "small_3_0"
# instance_size = "micro_ipv6_3_0"
instance_size = "micro_3_0" 
region = "eu-central-1"
private_key_path = "~/.ssh/id_rsa"  # Update this with the path to your private key

instances = []

# Create 1 Master Instance
master_instance = lightsail.Instance(f"master-0",
        availability_zone=f"{region}a",
        blueprint_id="ubuntu_22_04",
        bundle_id=master_instance_size,
        ip_address_type="dualstack",
        key_pair_name="id_rsa",
    )
# Create Security Group to open necessary ports
master_sg = lightsail.InstancePublicPorts("master-ports",
    instance_name=master_instance.name,
    port_infos=[
        lightsail.InstancePublicPortsPortInfoArgs(from_port=22, to_port=22, protocol="tcp"),
        lightsail.InstancePublicPortsPortInfoArgs(from_port=6443, to_port=6443, protocol="tcp"),  # Kubernetes API server
        lightsail.InstancePublicPortsPortInfoArgs(from_port=3000, to_port=3000, protocol="tcp"),  # Grafana
        lightsail.InstancePublicPortsPortInfoArgs(from_port=9090, to_port=9090, protocol="tcp"),  # Prometheus
    ]
)

# Export instance details
pulumi.export("master_instance_ip", master_instance.public_ip_address)

# Create 2 Worker Instances
for i in range(2):
    instance = lightsail.Instance(f"worker-{i}",
        availability_zone=f"{region}a",
        blueprint_id="ubuntu_22_04",
        bundle_id=instance_size,
        # ip_address_type="ipv6",
        ip_address_type="dualstack",
        key_pair_name="id_rsa",
    )
    worker_sg = lightsail.InstancePublicPorts(f"worker-port-{i}",
        instance_name=instance.name,
        port_infos=[
            lightsail.InstancePublicPortsPortInfoArgs(from_port=22, to_port=22, protocol="tcp"),
        ]
    )
    instances.append(instance)

# Collect instance information
instance_info = [{
    "name": instance._name,
    "public_ipv6": instance.ipv6_addresses.apply(lambda ips: ips[0]),
    "public_ipv4": instance.public_ip_address,
    "ipv4": instance.private_ip_address,
    "group": "worker",
} for instance in instances]

instance_info.append(
    {
        "name": master_instance._name,
        "public_ipv6": master_instance.ipv6_addresses.apply(lambda ips: ips[0]),
        "public_ipv4": master_instance.public_ip_address,
        "ipv4": master_instance.private_ip_address,
        "group": "master",
    }
)



# Write the inventory.yaml file
def create_inventory_file(instance_info):
    def write_inventory(info):
        master_ip = info[-1]["ipv4"]
        inventory = {"all": {"vars": {"master_ip": master_ip}} ,"master": {"hosts": {}}, "worker": {"hosts": {}}}
        hosts_content = ""
        hosts_list = {}
        for instance in info:
            name = instance["name"]
            # public_ipv6 = instance["public_ipv6"]
            public_ipv4 = instance["public_ipv4"]
            local_ipv4 = instance["ipv4"]
            group = instance["group"]
            inventory[group]["hosts"][name] = {
                "ansible_host": public_ipv4,
                "local_ipv4": local_ipv4,
                "ansible_user": "ubuntu",
                "ansible_ssh_private_key_file": private_key_path
            }
            hosts_content += f"{local_ipv4} {name}\n"
            hosts_list[name] = local_ipv4
        with open("../ansible/inventory.yml", "w") as f:
            yaml.dump(inventory, f)
        with open("../ansible/hosts", "w") as f:
            f.write(hosts_content)
        with open("../ansible/hosts.yml", "w") as f:
            hosts_dict = {"additional_hosts" : hosts_list}
            yaml.dump(hosts_dict, f)
    pulumi.Output.all(*instance_info).apply(write_inventory)

create_inventory_file(instance_info)

# create_inventory_file(outputs)
# Output.all(ins = instances).apply(lambda args: create_inventory_file(args["ins"]))