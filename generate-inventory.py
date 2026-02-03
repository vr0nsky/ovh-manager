#!/usr/bin/env python3
"""
Legge terraform.tfstate e genera l'inventory Ansible per le VM OVH.

Uso:
  ./generate-inventory.py            # Genera ansible/inventory/hosts.yml
  ./generate-inventory.py --list     # Stampa l'inventory a schermo
"""

import json
import sys
import os

TFSTATE = os.path.join(os.path.dirname(__file__), "terraform.tfstate")
INVENTORY_FILE = os.path.join(os.path.dirname(__file__), "ansible", "inventory", "hosts.yml")


def load_instances():
    """Estrae le VM dal terraform.tfstate"""
    with open(TFSTATE) as f:
        state = json.load(f)

    instances = []
    for resource in state.get("resources", []):
        if resource.get("type") != "ovh_cloud_project_instance":
            continue
        if resource.get("mode") != "managed":
            continue

        for inst in resource.get("instances", []):
            attrs = inst.get("attributes", {})
            name = attrs.get("name", resource.get("name", "unknown"))
            region = attrs.get("region", "")

            # Trova IP pubblico dalle addresses
            public_ip = None
            private_ip = None
            for addr in attrs.get("addresses", []):
                if addr.get("version") == 4:
                    if "Ext-Net" in addr.get("network_name", ""):
                        public_ip = addr.get("ip")
                    else:
                        private_ip = addr.get("ip")

            # Fallback: se non troviamo Ext-Net, prendi il primo IPv4
            if not public_ip:
                for addr in attrs.get("addresses", []):
                    if addr.get("version") == 4 and addr.get("ip"):
                        public_ip = addr["ip"]
                        break

            if public_ip:
                instances.append({
                    "name": name,
                    "ip": public_ip,
                    "private_ip": private_ip,
                    "region": region,
                    "flavor": attrs.get("flavor_name", ""),
                    "image": attrs.get("image_name", ""),
                })

    return instances


def generate_yaml(instances):
    """Genera inventory YAML"""
    lines = ["all:", "  hosts:"]

    if not instances:
        lines.append("    # Nessuna VM trovata nel tfstate")
        lines.append("    # Crea una VM con: ./add-resource.py && terraform apply")
        return "\n".join(lines) + "\n"

    for inst in instances:
        lines.append(f"    {inst['name']}:")
        lines.append(f"      ansible_host: {inst['ip']}")
        if inst.get("private_ip"):
            lines.append(f"      private_ip: {inst['private_ip']}")
        if inst.get("region"):
            lines.append(f"      ovh_region: {inst['region']}")
        if inst.get("flavor"):
            lines.append(f"      ovh_flavor: {inst['flavor']}")
        if inst.get("image"):
            lines.append(f"      ovh_image: {inst['image']}")

    return "\n".join(lines) + "\n"


def main():
    if not os.path.exists(TFSTATE):
        print(f"Errore: {TFSTATE} non trovato")
        print("Esegui prima: terraform apply")
        sys.exit(1)

    instances = load_instances()

    inventory = generate_yaml(instances)

    if "--list" in sys.argv:
        print(inventory)
        print(f"Trovate {len(instances)} VM")
        return

    # Crea directory se non esiste
    os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)

    with open(INVENTORY_FILE, "w") as f:
        f.write(inventory)

    print(f"Inventory generato: {INVENTORY_FILE}")
    print(f"VM trovate: {len(instances)}")

    if instances:
        print()
        for inst in instances:
            print(f"  - {inst['name']}: {inst['ip']}")
        print()
        print("Ora puoi fare:")
        print("  cd ansible")
        print("  ansible-playbook playbooks/ping.yml       # Test connessione")
        print("  ansible-playbook playbooks/setup-base.yml  # Setup base")
    else:
        print()
        print("Nessuna VM trovata. Crea una VM con:")
        print("  ./add-resource.py")
        print("  terraform apply")
        print("  ./generate-inventory.py")


if __name__ == "__main__":
    main()
