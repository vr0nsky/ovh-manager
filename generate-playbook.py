#!/usr/bin/env python3
"""
Genera playbook Ansible personalizzati per le VM OVH.
Legge i servizi da ansible/services.yml e le VM dal terraform.tfstate.

Uso:
  ./generate-playbook.py
"""

import json
import os
import sys
from collections import OrderedDict

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TFSTATE = os.path.join(BASE_DIR, "terraform.tfstate")
INVENTORY_FILE = os.path.join(BASE_DIR, "ansible", "inventory", "hosts.yml")
PLAYBOOKS_DIR = os.path.join(BASE_DIR, "ansible", "playbooks")
SERVICES_FILE = os.path.join(BASE_DIR, "ansible", "services.yml")


# =============================================================================
# Caricamento dati
# =============================================================================

def load_services():
    """Carica il catalogo servizi da services.yml"""
    if not os.path.exists(SERVICES_FILE):
        print(f"Errore: {SERVICES_FILE} non trovato")
        sys.exit(1)
    with open(SERVICES_FILE) as f:
        return yaml.safe_load(f)


def load_hosts():
    """Carica le VM direttamente dal terraform.tfstate"""
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

            # Trova IP pubblico
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
                hosts[name] = {
                    "ansible_host": public_ip,
                    "ovh_region": attrs.get("region", ""),
                    "ovh_flavor": attrs.get("flavor_name", ""),
                }

    # Rigenera anche l'inventory file per ansible-playbook
    if hosts:
        os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)
        inv = {"all": {"hosts": hosts}}
        with open(INVENTORY_FILE, "w") as f:
            yaml.dump(inv, f, default_flow_style=False, sort_keys=False)

    return hosts


# =============================================================================
# UI
# =============================================================================

def clear():
    os.system("clear")


def select_host(hosts):
    """Scegli una VM o tutte"""
    clear()
    print("=" * 60)
    print("  SCEGLI VM")
    print("=" * 60)
    print()

    names = list(hosts.keys())
    print("  1. ** Tutte le VM **")
    for i, name in enumerate(names, 2):
        ip = hosts[name].get("ansible_host", "?")
        print(f"  {i}. {name:<20} {ip}")
    print()
    print("  0. Annulla")
    print()

    while True:
        try:
            choice = input("Scegli [numero]: ").strip()
            if choice == "0":
                return None
            idx = int(choice)
            if idx == 1:
                return "all"
            if 2 <= idx <= len(names) + 1:
                return names[idx - 2]
        except (ValueError, IndexError):
            pass
        print("Scelta non valida")


def select_services(services):
    """Scegli i servizi raggruppati per categoria"""
    clear()
    print("=" * 60)
    print("  SCEGLI SERVIZI DA INSTALLARE")
    print("=" * 60)
    print()

    # Raggruppa per categoria
    categories = OrderedDict()
    keys_list = list(services.keys())
    for key in keys_list:
        svc = services[key]
        cat = svc.get("category", "Altro")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(key)

    # Mostra con numeri progressivi
    num = 1
    num_to_key = {}
    for cat, svc_keys in categories.items():
        print(f"  [{cat}]")
        for key in svc_keys:
            svc = services[key]
            print(f"  {num:3}. {svc['name']:<28} {svc['desc']}")
            num_to_key[num] = key
            num += 1
        print()

    print("  Inserisci i numeri separati da virgola (es: 1,4,5,10)")
    print("  0 = Annulla")
    print()

    while True:
        raw = input("Servizi: ").strip()
        if raw == "0":
            return None
        try:
            indices = [int(x.strip()) for x in raw.split(",")]
            selected = []
            for idx in indices:
                if idx in num_to_key:
                    selected.append(num_to_key[idx])
                else:
                    raise ValueError
            if selected:
                return selected
        except ValueError:
            pass
        print("Input non valido")


def generate_playbook(target, selected_services, services):
    """Genera il playbook YAML"""
    tasks = []
    for svc_key in selected_services:
        svc = services[svc_key]
        tasks.append({
            "name": f"--- {svc['name']} ---",
            "ansible.builtin.debug": {"msg": f"Installazione {svc['name']}..."},
        })
        tasks.extend(svc["tasks"])

    if target == "all":
        hosts = "all"
        filename = "setup-custom.yml"
    else:
        filename = f"setup-{target.lower().replace(' ', '-')}.yml"
        hosts = target

    playbook = [
        {
            "name": f"Setup {target}",
            "hosts": hosts,
            "become": True,
            "gather_facts": True,
            "tasks": tasks,
        }
    ]

    return filename, playbook


def playbook_to_yaml(playbook):
    """Converte il playbook in YAML leggibile"""
    return yaml.dump(
        playbook,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


# =============================================================================
# Main
# =============================================================================

def main():
    services = load_services()

    hosts = load_hosts()
    if not hosts:
        print("Nessuna VM trovata nel terraform.tfstate.")
        print("Esegui prima:")
        print("  ./add-resource.py     # Crea VM")
        print("  terraform apply       # Applica")
        sys.exit(1)

    print(f"Trovate {len(hosts)} VM nel tfstate")
    for name, info in hosts.items():
        print(f"  - {name}: {info['ansible_host']}")
    print()

    # 1. Scegli VM
    target = select_host(hosts)
    if not target:
        print("Annullato")
        return

    # 2. Scegli servizi
    selected = select_services(services)
    if not selected:
        print("Annullato")
        return

    # 3. Genera playbook
    filename, playbook = generate_playbook(target, selected, services)
    playbook_yaml = playbook_to_yaml(playbook)

    # 4. Preview
    clear()
    print("=" * 60)
    print("  ANTEPRIMA PLAYBOOK")
    print("=" * 60)
    print()
    print(f"  VM:       {target}")
    print(f"  Servizi:  {', '.join(services[s]['name'] for s in selected)}")
    print(f"  File:     ansible/playbooks/{filename}")
    print()
    print("-" * 60)
    print(playbook_yaml)
    print("-" * 60)
    print()

    confirm = input("Salvare il playbook? (s/n) [s]: ").strip().lower()
    if confirm in ("s", ""):
        filepath = os.path.join(PLAYBOOKS_DIR, filename)
        with open(filepath, "w") as f:
            f.write("---\n")
            f.write(f"# Playbook generato per: {target}\n")
            f.write(f"# Servizi: {', '.join(services[s]['name'] for s in selected)}\n")
            f.write(f"# Uso: ansible-playbook playbooks/{filename}\n\n")
            f.write(playbook_yaml)

        print()
        print(f"Playbook salvato: ansible/playbooks/{filename}")
        print()
        print("Ora esegui:")
        print(f"  cd ansible")
        print(f"  ansible-playbook playbooks/{filename}")
    else:
        print("Annullato")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrotto")
