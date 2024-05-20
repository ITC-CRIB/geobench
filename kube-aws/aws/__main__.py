"""An AWS Python Pulumi program"""

import pulumi
from pulumi_aws import lightsail
from pulumi import Output
import yaml

# Configuration
# instance_size = "small_ipv6_3_0"  # 2 GB RAM instance type
instance_size = "micro_ipv6_3_0" 
region = "eu-central-1"
private_key_path = "~/.ssh/id_rsa"  # Update this with the path to your private key

instances = []

# Create 1 Master Instance
master_instance = lightsail.Instance(f"master",
        availability_zone=f"{region}a",
        blueprint_id="ubuntu_22_04",
        bundle_id=instance_size,
        ip_address_type="ipv6",
    )

# Create 2 Worker Instances
for i in range(2):
    instance = lightsail.Instance(f"worker-{i}",
        availability_zone=f"{region}a",
        blueprint_id="ubuntu_22_04",
        bundle_id=instance_size,
        ip_address_type="ipv6",
    )
    instances.append(instance)

# Collect instance information
instance_info = [{
    "name": instance._name,
    "ipv6": instance.ipv6_addresses.apply(lambda ips: ips[0]),
    "ipv4": instance.private_ip_address,
    "group": "worker",
} for instance in instances]

instance_info.append(
    {
        "name": master_instance._name,
        "ipv6": master_instance.ipv6_addresses.apply(lambda ips: ips[0]),
        "ipv4": master_instance.private_ip_address,
        "group": "master",
    }
)

# Write the inventory.yaml file
def create_inventory_file(instance_info):
    def write_inventory(info):
        inventory = {"master": {"hosts": {}}, "worker": {"hosts": {}}}
        hosts_content = ""
        for instance in info:
            name = instance["name"]
            public_ipv6 = instance["ipv6"]
            local_ipv4 = instance["ipv4"]
            group = instance["group"]
            inventory[group]["hosts"][name] = {
                "ansible_host": public_ipv6,
                "local_ipv4": local_ipv4,
                "ansible_user": "ubuntu",
                "ansible_ssh_private_key_file": private_key_path
            }
            hosts_content += f"{local_ipv4} {name}\n"
        with open("../ansible/inventory.yml", "w") as f:
            yaml.dump(inventory, f)
        with open("../ansible/hosts", "w") as f:
            f.write(hosts_content)
    pulumi.Output.all(*instance_info).apply(write_inventory)

create_inventory_file(instance_info)

# create_inventory_file(outputs)
# Output.all(ins = instances).apply(lambda args: create_inventory_file(args["ins"]))