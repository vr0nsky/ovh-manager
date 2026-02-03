# OVH Manager

CLI tool for managing OVH Public Cloud infrastructure with Terraform and Ansible.

Create VMs, configure them with pre-built service recipes, and connect via SSH — all from a single interactive menu.

**[Project Homepage](https://massimoivaldi.com/ovh-manager)**

## Features

- **Interactive VM management** — create and destroy instances with a guided wizard
- **Dynamic Ansible playbooks** — pick services from a catalog, generate a playbook, run it
- **30+ services catalog** — Nginx, Apache, PHP, Docker, PostgreSQL, Node.js, and more (easily extensible via YAML)
- **Guided procedures** — full workflows like "Deploy Web Server" that chain VM creation, Terraform apply, playbook generation, and SSH connection
- **SSH connect** — jump into any VM directly from the menu
- **System monitoring** — check CPU, RAM, disk, running services across all VMs
- **Ad-hoc commands** — run any command on remote VMs without writing a playbook
- **First-run setup** — walks you through OVH API credentials configuration

## Quick Start

```bash
git clone https://github.com/vr0nsky/ovh-manager.git
cd ovh-manager
./ovhmanager.py
```

On first run, the tool will ask for your OVH API credentials and initialize Terraform.

### Prerequisites

- Python 3.10+
- Terraform 1.0+
- Ansible 2.14+
- [OVH API credentials](https://www.ovh.com/auth/api/createToken)

Install dependencies:

```bash
# Debian/Ubuntu
apt install ansible terraform python3-ovh python3-yaml

# Or via pip (for ovh + hcl2)
pip install python-ovh pyhcl2 pyyaml
```

## Usage

```bash
./ovhmanager.py
```

```
============================================================
  OVH MANAGER
============================================================

  Credenziali: OK  |  Terraform: OK  |  VM attive: 2
    - web-server: 51.x.x.x
    - docker-host: 54.x.x.x

  1. [Infrastruttura]  Crea, rimuovi, gestisci risorse
  2. [Ansible]         Configura, deploya, comandi remoti
  3. [Procedure]       Workflow guidati (web server, docker...)
  4. [SSH]             Connetti a una VM
  5. [Setup]           Riconfigura credenziali OVH

  0. Esci
```

### Individual scripts

Each component can also be used standalone:

| Script | Description |
|---|---|
| `add-resource.py` | Interactive wizard to add a VM or volume |
| `remove-resource.py` | Remove a resource from Terraform files |
| `generate-inventory.py` | Generate Ansible inventory from Terraform state |
| `generate-playbook.py` | Generate a custom playbook from the service catalog |
| `connect.py` | SSH into a VM (`./connect.py` or `./connect.py vm-name`) |
| `ovh-check.py` | Show current OVH resources via API |

## Service Catalog

Services are defined in `ansible/services.yml`. Pick any combination when generating a playbook:

| Category | Services |
|---|---|
| **System** | Base setup, Swap |
| **Web Server** | Nginx, Apache, Caddy, Certbot |
| **Languages** | PHP 8.x + FPM, Composer, Node.js 22, Python 3, Go, Ruby, Java 21, Rust |
| **Database** | PostgreSQL, MariaDB, MongoDB, SQLite |
| **Cache / Queue** | Redis, Memcached, RabbitMQ |
| **Container** | Docker + Compose, Portainer |
| **Security** | Fail2ban, UFW Firewall, ClamAV, WireGuard VPN |
| **Monitoring** | Node Exporter, Netdata |
| **Stacks** | LAMP, LEMP, MEAN |
| **Tools** | phpMyAdmin, Adminer, MinIO |

To add a new service, just edit `ansible/services.yml` — no code changes needed.

## Guided Procedures

Pre-built workflows that chain multiple steps:

- **Deploy Web Server** — Create VM, apply Terraform, generate playbook (Nginx + PHP + SSL + Firewall), run it, connect via SSH
- **Deploy Docker Host** — Create VM, apply Terraform, install Docker + Compose + Portainer, connect via SSH
- **Remove VM** — Select resource, remove from Terraform, apply to destroy

## Project Structure

```
ovh-manager/
├── ovhmanager.py              # Main entry point
├── add-resource.py            # VM/volume creation wizard
├── remove-resource.py         # Resource removal
├── generate-inventory.py      # Terraform state → Ansible inventory
├── generate-playbook.py       # Service catalog → Ansible playbook
├── connect.py                 # SSH connection helper
├── ovh-check.py               # OVH API resource checker
├── setup.sh                   # Credential setup (standalone)
├── main.tf                    # Terraform resources
├── outputs.tf                 # Terraform outputs
├── providers.tf               # OVH provider config
├── variables.tf               # Terraform variables
├── versions.tf                # Provider versions
├── terraform.tfvars.example   # Example configuration
└── ansible/
    ├── ansible.cfg            # Ansible configuration
    ├── services.yml           # Service catalog (editable)
    ├── inventory/
    │   └── hosts.yml          # Auto-generated from Terraform state
    └── playbooks/
        ├── ping.yml           # Connection test
        ├── setup-base.yml     # Base server setup
        └── system-info.yml    # System resource monitoring
```

## How It Works

```
                    ┌─────────────────┐
                    │   ovhmanager.py │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
   ┌────────▼──────┐ ┌──────▼──────┐ ┌───────▼──────┐
   │  Terraform    │ │   Ansible   │ │    SSH       │
   │  (create VM)  │ │ (configure) │ │  (connect)   │
   └────────┬──────┘ └──────┬──────┘ └──────────────┘
            │                │
     ┌──────▼──────┐  ┌─────▼──────┐
     │  OVH API    │  │  VM via    │
     │  (provider) │  │  SSH       │
     └─────────────┘  └────────────┘
```

1. **Terraform** creates infrastructure on OVH (VMs, networks, volumes)
2. **Ansible** configures VMs over SSH (packages, services, security)
3. The tool reads `terraform.tfstate` to always know current VMs and IPs
4. Inventory and playbooks are generated dynamically — no manual editing

## License

MIT
