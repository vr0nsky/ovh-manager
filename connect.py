#!/usr/bin/env python3
"""
Apre una shell SSH su una VM OVH.
Legge le VM dal terraform.tfstate.

Uso:
  ./connect.py              # Menu interattivo
  ./connect.py nome-vm      # Connessione diretta
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TFSTATE = os.path.join(BASE_DIR, "terraform.tfstate")
SSH_USER = "ubuntu"


def load_hosts():
    """Carica le VM dal terraform.tfstate"""
    if not os.path.exists(TFSTATE):
        return {}

    with open(TFSTATE) as f:
        state = json.load(f)

    hosts = {}
    for resource in state.get("resources", []):
        if resource.get("type") != "ovh_cloud_project_instance":
            continue
        if resource.get("mode") != "managed":
            continue

        for inst in resource.get("instances", []):
            attrs = inst.get("attributes", {})
            name = attrs.get("name", resource.get("name", "unknown"))

            public_ip = None
            for addr in attrs.get("addresses", []):
                if addr.get("version") == 4:
                    if "Ext-Net" in addr.get("network_name", ""):
                        public_ip = addr.get("ip")
                        break
            if not public_ip:
                for addr in attrs.get("addresses", []):
                    if addr.get("version") == 4 and addr.get("ip"):
                        public_ip = addr["ip"]
                        break

            if public_ip:
                hosts[name] = public_ip

    return hosts


def main():
    hosts = load_hosts()
    if not hosts:
        print("Nessuna VM trovata nel terraform.tfstate.")
        sys.exit(1)

    # Connessione diretta se passato il nome
    if len(sys.argv) > 1:
        name = sys.argv[1]
        # Cerca match case-insensitive
        for h, ip in hosts.items():
            if h.lower() == name.lower():
                print(f"Connessione a {h} ({ip})...")
                os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", f"{SSH_USER}@{ip}"])
        print(f"VM '{name}' non trovata.")
        sys.exit(1)

    # Menu interattivo
    print("=" * 40)
    print("  CONNETTI A VM")
    print("=" * 40)
    print()

    names = list(hosts.keys())
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name:<20} {hosts[name]}")
    print()
    print("  0. Annulla")
    print()

    while True:
        try:
            choice = input("Scegli [numero]: ").strip()
            if choice == "0":
                return
            idx = int(choice) - 1
            if 0 <= idx < len(names):
                name = names[idx]
                ip = hosts[name]
                print(f"\nConnessione a {name} ({ip})...\n")
                os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", f"{SSH_USER}@{ip}"])
        except (ValueError, IndexError):
            pass
        print("Scelta non valida")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrotto")
