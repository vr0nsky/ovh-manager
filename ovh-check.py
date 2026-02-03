#!/usr/bin/env python3
"""
Mostra le risorse OVH Public Cloud
Usa le credenziali da ~/.ovh.conf
"""

import ovh
import json
import sys

# Legge credenziali da ~/.ovh.conf automaticamente
client = ovh.Client()

PROJECT_ID = "070604d9c73f4bb4b7b0c11908643247"

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print('='*50)

# Info progetto
print_section("PROGETTO")
project = client.get(f"/cloud/project/{PROJECT_ID}")
print(f"ID: {project.get('project_id', PROJECT_ID)}")
print(f"Descrizione: {project.get('description', 'N/A')}")
print(f"Stato: {project.get('status', 'N/A')}")

# Reti private
print_section("RETI PRIVATE")
networks = client.get(f"/cloud/project/{PROJECT_ID}/network/private")
if networks:
    for net in networks:
        print(f"- {net['name']} (VLAN: {net.get('vlanId', 'N/A')}, ID: {net['id']})")
else:
    print("(nessuna)")

# SSH Keys
print_section("SSH KEYS")
try:
    # Prova prima il nuovo endpoint
    keys = client.get(f"/cloud/project/{PROJECT_ID}/sshkey")
    if keys:
        for key in keys:
            print(f"- {key['name']} ({key.get('fingerPrint', key.get('finger_print', 'N/A'))})")
    else:
        print("(nessuna)")
except:
    print("(impossibile leggere)")

# Istanze (VM)
print_section("ISTANZE (VM)")
instances = client.get(f"/cloud/project/{PROJECT_ID}/instance")
if instances:
    for vm in instances:
        ips = [addr['ip'] for addr in vm.get('ipAddresses', [])]
        print(f"- {vm['name']} ({vm.get('status', 'N/A')}) - {', '.join(ips) or 'no IP'}")
else:
    print("(nessuna)")

# Volumi
print_section("VOLUMI (DISCHI)")
try:
    volumes = client.get(f"/cloud/project/{PROJECT_ID}/volume")
    if volumes:
        for vol in volumes:
            print(f"- {vol['name']} ({vol.get('size', '?')} GB, {vol.get('status', 'N/A')})")
    else:
        print("(nessuno)")
except:
    print("(nessuno)")

print()
