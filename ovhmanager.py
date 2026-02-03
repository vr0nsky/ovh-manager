#!/usr/bin/env python3
"""
OVH Manager - Gestione completa infrastruttura OVH Public Cloud
Integra: Setup credenziali, Terraform, Ansible, SSH

Uso:
  ./ovhmanager.py
"""

import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TFSTATE = os.path.join(BASE_DIR, "terraform.tfstate")
OVH_CONF = os.path.expanduser("~/.ovh.conf")
TFVARS = os.path.join(BASE_DIR, "terraform.tfvars")
INVENTORY_FILE = os.path.join(BASE_DIR, "ansible", "inventory", "hosts.yml")
PLAYBOOKS_DIR = os.path.join(BASE_DIR, "ansible", "playbooks")
ANSIBLE_DIR = os.path.join(BASE_DIR, "ansible")
SSH_USER = "ubuntu"


# =============================================================================
# Utilità
# =============================================================================

def clear():
    os.system("clear")


def pause(msg="Premi INVIO per continuare..."):
    input(msg)


def run(cmd, cwd=None):
    """Esegue un comando e mostra l'output in tempo reale"""
    return subprocess.call(cmd, shell=True, cwd=cwd or BASE_DIR)


def run_capture(cmd, cwd=None):
    """Esegue un comando e cattura l'output"""
    result = subprocess.run(cmd, shell=True, cwd=cwd or BASE_DIR,
                            capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def banner(title):
    clear()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def menu(title, options):
    """Menu generico. Ritorna la chiave scelta o None"""
    banner(title)
    for i, (key, label) in enumerate(options, 1):
        print(f"  {i:2}. {label}")
    print()
    print("   0. Indietro")
    print()

    while True:
        try:
            choice = input("Scegli: ").strip()
            if choice == "0":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except (ValueError, IndexError):
            pass
        print("  Scelta non valida")


# =============================================================================
# Stato infrastruttura
# =============================================================================

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
            private_ip = None
            for addr in attrs.get("addresses", []):
                if addr.get("version") == 4:
                    if "Ext-Net" in addr.get("network_name", ""):
                        public_ip = addr.get("ip")
                    else:
                        private_ip = addr.get("ip")
            if not public_ip:
                for addr in attrs.get("addresses", []):
                    if addr.get("version") == 4 and addr.get("ip"):
                        public_ip = addr["ip"]
                        break

            if public_ip:
                hosts[name] = {
                    "ip": public_ip,
                    "private_ip": private_ip,
                    "region": attrs.get("region", ""),
                    "flavor": attrs.get("flavor_name", ""),
                    "image": attrs.get("image_name", ""),
                }

    return hosts


def sync_inventory(hosts):
    """Aggiorna l'inventory Ansible dal tfstate"""
    import yaml
    os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)
    inv_hosts = {}
    for name, info in hosts.items():
        inv_hosts[name] = {
            "ansible_host": info["ip"],
            "ovh_region": info.get("region", ""),
            "ovh_flavor": info.get("flavor", ""),
        }
    inv = {"all": {"hosts": inv_hosts}} if inv_hosts else {"all": {"hosts": {}}}
    with open(INVENTORY_FILE, "w") as f:
        yaml.dump(inv, f, default_flow_style=False, sort_keys=False)


def select_vm(hosts, allow_all=False):
    """Menu per scegliere una VM"""
    if not hosts:
        print("  Nessuna VM trovata.")
        pause()
        return None

    banner("SCEGLI VM")
    names = list(hosts.keys())
    start = 1
    if allow_all:
        print("  1. ** Tutte le VM **")
        start = 2

    for i, name in enumerate(names, start):
        info = hosts[name]
        print(f"  {i}. {name:<20} {info['ip']:<16} {info.get('flavor', '')}")
    print()
    print("  0. Annulla")
    print()

    while True:
        try:
            choice = input("Scegli: ").strip()
            if choice == "0":
                return None
            idx = int(choice)
            if allow_all and idx == 1:
                return "all"
            offset = 0 if not allow_all else 1
            real_idx = idx - 1 - offset
            if 0 <= real_idx < len(names):
                return names[real_idx]
        except (ValueError, IndexError):
            pass
        print("  Scelta non valida")


# =============================================================================
# 1. SETUP
# =============================================================================

def check_setup():
    """Verifica se le credenziali sono configurate"""
    return os.path.exists(OVH_CONF) and os.path.exists(TFVARS)


def check_terraform_init():
    """Verifica se terraform è inizializzato"""
    return os.path.exists(os.path.join(BASE_DIR, ".terraform"))


def do_setup():
    """Setup interattivo delle credenziali OVH"""
    banner("SETUP CREDENZIALI OVH")

    print("  Per usare questo tool hai bisogno delle chiavi API OVH.")
    print()
    print("  1. Vai su: https://www.ovh.com/auth/api/createToken")
    print()
    print("  2. Compila il form:")
    print("     - Application name: terraform")
    print("     - Application description: Terraform automation")
    print("     - Validity: Unlimited")
    print("     - Rights: GET /*, POST /*, PUT /*, DELETE /*")
    print()
    print("  3. Copia le chiavi generate e incollale qui sotto.")
    print()
    print("  4. Per il Project ID:")
    print("     OVH Manager > Public Cloud > Il tuo progetto > Project Settings")
    print()

    app_key = input("  OVH_APPLICATION_KEY: ").strip()
    if not app_key:
        print("  Annullato.")
        pause()
        return False

    app_secret = input("  OVH_APPLICATION_SECRET: ").strip()
    consumer_key = input("  OVH_CONSUMER_KEY: ").strip()
    project_id = input("  PROJECT_ID: ").strip()

    if not all([app_key, app_secret, consumer_key, project_id]):
        print("\n  Tutti i campi sono obbligatori!")
        pause()
        return False

    # Scrivi ~/.ovh.conf
    with open(OVH_CONF, "w") as f:
        f.write("[default]\n")
        f.write("endpoint=ovh-eu\n\n")
        f.write("[ovh-eu]\n")
        f.write(f"application_key={app_key}\n")
        f.write(f"application_secret={app_secret}\n")
        f.write(f"consumer_key={consumer_key}\n")
    os.chmod(OVH_CONF, 0o600)

    # Scrivi terraform.tfvars
    with open(TFVARS, "w") as f:
        f.write(f'service_name = "{project_id}"\n')
        f.write('region       = "GRA9"\n')
        f.write('environment  = "dev"\n')
        f.write('project_name = "myproject"\n')

    # Esporta variabili per la sessione corrente
    os.environ["OVH_APPLICATION_KEY"] = app_key
    os.environ["OVH_APPLICATION_SECRET"] = app_secret
    os.environ["OVH_CONSUMER_KEY"] = consumer_key
    os.environ["OVH_ENDPOINT"] = "ovh-eu"

    print()
    print("  Credenziali salvate!")
    print(f"  - {OVH_CONF}")
    print(f"  - {TFVARS}")
    print()

    # Terraform init
    print("  Inizializzo Terraform...")
    print()
    rc = run("terraform init", cwd=BASE_DIR)
    print()
    if rc == 0:
        print("  Setup completato!")
    else:
        print("  Terraform init fallito. Controlla le credenziali.")

    pause()
    return rc == 0


def do_reconfig():
    """Riconfigura le credenziali"""
    banner("RICONFIGURA CREDENZIALI")
    print("  Le credenziali attuali verranno sovrascritte.")
    print()
    confirm = input("  Continuare? (s/n) [n]: ").strip().lower()
    if confirm == "s":
        do_setup()


# =============================================================================
# 2. INFRASTRUTTURA
# =============================================================================

def do_check_infra():
    """Mostra le risorse OVH via API"""
    banner("RISORSE OVH")
    run(f"python3 {os.path.join(BASE_DIR, 'ovh-check.py')}")
    print()
    pause()


def do_add_resource():
    """Aggiungi una risorsa"""
    run(f"python3 {os.path.join(BASE_DIR, 'add-resource.py')}")


def do_remove_resource():
    """Rimuovi una risorsa"""
    run(f"python3 {os.path.join(BASE_DIR, 'remove-resource.py')}")


def do_terraform_plan():
    """Mostra il piano Terraform"""
    banner("TERRAFORM PLAN")
    run("terraform plan", cwd=BASE_DIR)
    print()
    pause()


def do_terraform_apply():
    """Applica le modifiche Terraform"""
    banner("TERRAFORM APPLY")
    rc = run("terraform apply", cwd=BASE_DIR)
    print()
    if rc == 0:
        hosts = load_hosts()
        sync_inventory(hosts)
        if hosts:
            print("  Inventory Ansible aggiornato automaticamente.")
            print()
    pause()


def menu_infra():
    """Sottomenu infrastruttura"""
    while True:
        hosts = load_hosts()
        n_vm = len(hosts)

        choice = menu(f"INFRASTRUTTURA ({n_vm} VM attive)", [
            ("check",   "Controlla risorse OVH (API)"),
            ("add",     "Crea nuova risorsa (VM/Volume)"),
            ("remove",  "Rimuovi risorsa"),
            ("plan",    "Terraform plan (anteprima)"),
            ("apply",   "Terraform apply (applica)"),
        ])

        if choice is None:
            break
        elif choice == "check":
            do_check_infra()
        elif choice == "add":
            do_add_resource()
        elif choice == "remove":
            do_remove_resource()
        elif choice == "plan":
            do_terraform_plan()
        elif choice == "apply":
            do_terraform_apply()


# =============================================================================
# 3. ANSIBLE
# =============================================================================

def do_generate_playbook():
    """Genera un playbook personalizzato"""
    run(f"python3 {os.path.join(BASE_DIR, 'generate-playbook.py')}")


def do_run_playbook():
    """Scegli ed esegui un playbook"""
    playbooks = sorted([
        f for f in os.listdir(PLAYBOOKS_DIR)
        if f.endswith(".yml") and f != "ping.yml"
    ])

    if not playbooks:
        banner("ESEGUI PLAYBOOK")
        print("  Nessun playbook trovato.")
        print("  Generane uno prima con 'Genera playbook'.")
        pause()
        return

    options = [("ping", "Test connessione (ping)")]
    for pb in playbooks:
        options.append((pb, pb))

    choice = menu("ESEGUI PLAYBOOK", options)
    if choice is None:
        return

    if choice == "ping":
        choice = "ping.yml"

    banner(f"ESECUZIONE: {choice}")
    run(f"ansible-playbook playbooks/{choice}", cwd=ANSIBLE_DIR)
    print()
    pause()


def do_system_info():
    """Mostra info sistema delle VM"""
    banner("INFO SISTEMA VM")
    hosts = load_hosts()
    sync_inventory(hosts)
    run(f"ansible-playbook playbooks/system-info.yml", cwd=ANSIBLE_DIR)
    print()
    pause()


def do_ansible_adhoc():
    """Esegui un comando su una VM"""
    hosts = load_hosts()
    target = select_vm(hosts, allow_all=True)
    if not target:
        return

    print()
    cmd = input("  Comando da eseguire: ").strip()
    if not cmd:
        return

    print()
    if target == "all":
        run(f'ansible all -m shell -a "{cmd}" --become', cwd=ANSIBLE_DIR)
    else:
        run(f'ansible {target} -m shell -a "{cmd}" --become', cwd=ANSIBLE_DIR)
    print()
    pause()


def menu_ansible():
    """Sottomenu Ansible"""
    while True:
        choice = menu("ANSIBLE - CONFIGURA VM", [
            ("generate", "Genera playbook personalizzato"),
            ("run",      "Esegui playbook"),
            ("info",     "Info sistema VM"),
            ("adhoc",    "Esegui comando remoto"),
        ])

        if choice is None:
            break
        elif choice == "generate":
            do_generate_playbook()
        elif choice == "run":
            do_run_playbook()
        elif choice == "info":
            do_system_info()
        elif choice == "adhoc":
            do_ansible_adhoc()


# =============================================================================
# 4. CONNESSIONE
# =============================================================================

def do_connect():
    """SSH a una VM"""
    hosts = load_hosts()
    target = select_vm(hosts)
    if not target:
        return

    ip = hosts[target]["ip"]
    print(f"\n  Connessione a {target} ({ip})...\n")
    os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", f"{SSH_USER}@{ip}"])


# =============================================================================
# 5. PROCEDURE GUIDATE
# =============================================================================

def proc_deploy_webserver():
    """Procedura: Deploy web server completo"""
    banner("PROCEDURA: DEPLOY WEB SERVER")
    print("  Questa procedura:")
    print("    1. Crea una nuova VM")
    print("    2. Applica con Terraform")
    print("    3. Genera un playbook con Nginx + PHP + Certbot + Fail2ban + UFW")
    print("    4. Esegue il playbook")
    print("    5. Ti connette alla VM")
    print()
    confirm = input("  Continuare? (s/n) [s]: ").strip().lower()
    if confirm not in ("s", ""):
        return

    # Step 1: Crea VM
    print("\n  STEP 1/5 - Crea la VM\n")
    run(f"python3 {os.path.join(BASE_DIR, 'add-resource.py')}")

    # Step 2: Terraform apply
    print("\n  STEP 2/5 - Terraform apply\n")
    rc = run("terraform apply", cwd=BASE_DIR)
    if rc != 0:
        print("\n  Terraform apply fallito!")
        pause()
        return

    # Aggiorna inventory
    hosts = load_hosts()
    sync_inventory(hosts)

    if not hosts:
        print("\n  Nessuna VM trovata dopo apply!")
        pause()
        return

    # Step 3: Genera playbook
    print("\n  STEP 3/5 - Genera playbook\n")
    run(f"python3 {os.path.join(BASE_DIR, 'generate-playbook.py')}")

    # Step 4: Esegui playbook
    print("\n  STEP 4/5 - Quale playbook eseguire?\n")
    playbooks = [f for f in os.listdir(PLAYBOOKS_DIR) if f.startswith("setup-")]
    if playbooks:
        for i, pb in enumerate(playbooks, 1):
            print(f"    {i}. {pb}")
        print()
        try:
            idx = int(input("  Scegli: ").strip()) - 1
            if 0 <= idx < len(playbooks):
                run(f"ansible-playbook playbooks/{playbooks[idx]}", cwd=ANSIBLE_DIR)
        except (ValueError, IndexError):
            print("  Saltato.")

    # Step 5: Connetti?
    print()
    conn = input("  STEP 5/5 - Connettersi alla VM via SSH? (s/n) [s]: ").strip().lower()
    if conn in ("s", ""):
        target = select_vm(hosts)
        if target:
            ip = hosts[target]["ip"]
            print(f"\n  Connessione a {target} ({ip})...\n")
            os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", f"{SSH_USER}@{ip}"])


def proc_deploy_docker():
    """Procedura: Deploy Docker host"""
    banner("PROCEDURA: DEPLOY DOCKER HOST")
    print("  Questa procedura:")
    print("    1. Crea una nuova VM")
    print("    2. Applica con Terraform")
    print("    3. Installa Docker + Compose + Portainer")
    print("    4. Ti connette alla VM")
    print()
    confirm = input("  Continuare? (s/n) [s]: ").strip().lower()
    if confirm not in ("s", ""):
        return

    # Step 1
    print("\n  STEP 1 - Crea la VM\n")
    run(f"python3 {os.path.join(BASE_DIR, 'add-resource.py')}")

    # Step 2
    print("\n  STEP 2 - Terraform apply\n")
    rc = run("terraform apply", cwd=BASE_DIR)
    if rc != 0:
        print("\n  Terraform apply fallito!")
        pause()
        return

    hosts = load_hosts()
    sync_inventory(hosts)

    # Step 3: Genera ed esegui playbook Docker
    print("\n  STEP 3 - Genera playbook\n")
    run(f"python3 {os.path.join(BASE_DIR, 'generate-playbook.py')}")

    # Esegui
    playbooks = [f for f in os.listdir(PLAYBOOKS_DIR) if f.startswith("setup-")]
    if playbooks:
        for i, pb in enumerate(playbooks, 1):
            print(f"    {i}. {pb}")
        print()
        try:
            idx = int(input("  Scegli playbook: ").strip()) - 1
            if 0 <= idx < len(playbooks):
                run(f"ansible-playbook playbooks/{playbooks[idx]}", cwd=ANSIBLE_DIR)
        except (ValueError, IndexError):
            pass

    # Step 4: Connetti
    print()
    conn = input("  Connettersi alla VM via SSH? (s/n) [s]: ").strip().lower()
    if conn in ("s", ""):
        target = select_vm(hosts)
        if target:
            ip = hosts[target]["ip"]
            os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", f"{SSH_USER}@{ip}"])


def proc_destroy():
    """Procedura: Rimuovi una VM"""
    banner("PROCEDURA: RIMUOVI VM")
    print("  Questa procedura:")
    print("    1. Mostra le VM attive")
    print("    2. Rimuove la risorsa dal file Terraform")
    print("    3. Applica con Terraform (distrugge la VM)")
    print()

    hosts = load_hosts()
    if hosts:
        for name, info in hosts.items():
            print(f"    - {name}: {info['ip']} ({info.get('flavor', '')})")
        print()

    confirm = input("  Continuare? (s/n) [s]: ").strip().lower()
    if confirm not in ("s", ""):
        return

    run(f"python3 {os.path.join(BASE_DIR, 'remove-resource.py')}")
    print()
    apply = input("  Eseguire terraform apply ora? (s/n) [s]: ").strip().lower()
    if apply in ("s", ""):
        run("terraform apply", cwd=BASE_DIR)
        hosts = load_hosts()
        sync_inventory(hosts)

    pause()


def menu_procedures():
    """Sottomenu procedure guidate"""
    while True:
        choice = menu("PROCEDURE GUIDATE", [
            ("web",     "Deploy Web Server (VM + Nginx/PHP/SSL/Firewall)"),
            ("docker",  "Deploy Docker Host (VM + Docker/Compose/Portainer)"),
            ("destroy", "Rimuovi VM (rimuovi + terraform apply)"),
        ])

        if choice is None:
            break
        elif choice == "web":
            proc_deploy_webserver()
        elif choice == "docker":
            proc_deploy_docker()
        elif choice == "destroy":
            proc_destroy()


# =============================================================================
# MAIN
# =============================================================================

def show_status():
    """Mostra lo stato attuale nell'header"""
    hosts = load_hosts()
    creds = "OK" if check_setup() else "MANCANTI"
    tf_init = "OK" if check_terraform_init() else "NO"

    print(f"  Credenziali: {creds}  |  Terraform: {tf_init}  |  VM attive: {len(hosts)}")
    if hosts:
        for name, info in hosts.items():
            print(f"    - {name}: {info['ip']}")
    print()


def main():
    # Primo avvio: controlla credenziali
    if not check_setup():
        banner("BENVENUTO IN OVH MANAGER")
        print("  Credenziali OVH non trovate.")
        print("  Avvio la configurazione iniziale...")
        print()
        pause()
        if not do_setup():
            print("  Setup non completato. Puoi rilanciare ./ovhmanager.py")
            sys.exit(1)

    # Terraform init se necessario
    if not check_terraform_init():
        banner("INIZIALIZZAZIONE TERRAFORM")
        print("  Terraform non inizializzato. Lo faccio ora...")
        print()
        run("terraform init", cwd=BASE_DIR)
        pause()

    # Menu principale
    while True:
        banner("OVH MANAGER")
        show_status()

        options = [
            ("infra",      "[Infrastruttura]  Crea, rimuovi, gestisci risorse"),
            ("ansible",    "[Ansible]         Configura, deploya, comandi remoti"),
            ("procedures", "[Procedure]       Workflow guidati (web server, docker...)"),
            ("connect",    "[SSH]             Connetti a una VM"),
            ("reconfig",   "[Setup]           Riconfigura credenziali OVH"),
        ]

        for i, (key, label) in enumerate(options, 1):
            print(f"  {i}. {label}")
        print()
        print("  0. Esci")
        print()

        try:
            choice = input("  Scegli: ").strip()
            if choice == "0":
                clear()
                print("Ciao!")
                break
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                key = options[idx][0]
                if key == "infra":
                    menu_infra()
                elif key == "ansible":
                    menu_ansible()
                elif key == "procedures":
                    menu_procedures()
                elif key == "connect":
                    do_connect()
                elif key == "reconfig":
                    do_reconfig()
        except (ValueError, IndexError):
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCiao!")
