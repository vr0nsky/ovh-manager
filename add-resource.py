#!/usr/bin/env python3
"""
Script interattivo per aggiungere risorse Terraform OVH
"""

import ovh
import os
import sys

client = ovh.Client()
PROJECT_ID = "070604d9c73f4bb4b7b0c11908643247"
REGION = "GRA9"
MAIN_TF = "/root/digitalocean/OVH/main.tf"

def clear():
    os.system('clear')

def menu(title, options):
    """Mostra menu e ritorna la scelta"""
    clear()
    print("=" * 60)
    print(f" {title}")
    print("=" * 60)
    print()

    for i, opt in enumerate(options, 1):
        if isinstance(opt, dict):
            price = opt.get('price', '')
            if price:
                print(f"  {i:2}. {opt['name']:<12} {opt.get('desc', ''):<25} {price}")
            else:
                print(f"  {i:2}. {opt['name']:<12} {opt.get('desc', '')}")
        else:
            print(f"  {i:2}. {opt}")

    print()
    print("   0. Annulla")
    print()

    while True:
        try:
            choice = input("Scegli [numero]: ").strip()
            if choice == '0':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx] if isinstance(options[idx], dict) else options[idx]
        except (ValueError, IndexError):
            pass
        print("Scelta non valida")

def input_text(prompt, default=""):
    """Input con default"""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()

def get_prices():
    """Ottiene i prezzi dal catalog OVH"""
    try:
        catalog = client.get("/order/catalog/public/cloud", ovhSubsidiary="IT")
        prices = {}
        for addon in catalog.get('addons', []):
            plan_code = addon.get('planCode', '')
            for pricing in addon.get('pricings', []):
                if 'consumption' in pricing.get('capacities', []):
                    # Prezzo in micro-centesimi -> euro
                    hourly = pricing.get('price', 0) / 100000000
                    prices[plan_code.replace('.consumption', '')] = hourly
        return prices
    except:
        return {}

def get_flavor_categories():
    """Raggruppa flavor per categoria"""
    categories = {
        'd2': 'Discovery (economiche)',
        'b2': 'Balanced Gen2 (generale)',
        'b3': 'Balanced Gen3 (generale)',
        'c2': 'CPU Gen2 (calcolo)',
        'c3': 'CPU Gen3 (calcolo)',
        'r2': 'RAM Gen2 (memoria)',
        'r3': 'RAM Gen3 (memoria)',
        'i1': 'IOPS (storage veloce)',
        't1': 'GPU T1',
        't2': 'GPU T2',
        'a10': 'GPU A10',
        'l4': 'GPU L4',
        'l40s': 'GPU L40S',
    }
    return categories

def get_flavors(category_prefix=None):
    """Ottiene i flavor disponibili con prezzi"""
    print("Caricamento flavor e prezzi...")
    flavors = client.get(f"/cloud/project/{PROJECT_ID}/flavor", region=REGION)
    prices = get_prices()

    result = []
    for f in sorted(flavors, key=lambda x: (x.get('ram', 0), x.get('name', ''))):
        if not f.get('available', True):
            continue

        name = f['name']

        # Filtra per categoria se specificata
        if category_prefix:
            # Gestisci prefissi con/senza win-
            base_name = name.replace('win-', '').replace('-flex', '')
            if not base_name.startswith(category_prefix):
                continue

        ram = f.get('ram', 0)
        vcpus = f.get('vcpus', '?')
        disk = f.get('disk', 0)
        os_type = "Win" if f.get('osType') == 'windows' else "Lin"

        # Cerca prezzo
        hourly = prices.get(name, 0)
        monthly = hourly * 730

        if hourly > 0:
            price_str = f"€{monthly:.2f}/m"
        else:
            price_str = ""

        result.append({
            'name': name,
            'id': f['id'],
            'desc': f"{vcpus}vCPU {ram}GB {disk}GB [{os_type}]",
            'price': price_str,
        })
    return result

def get_images():
    """Ottiene le immagini disponibili"""
    print("Caricamento immagini...")
    images = client.get(f"/cloud/project/{PROJECT_ID}/image", region=REGION)
    result = []
    seen = set()
    for img in sorted(images, key=lambda x: x.get('name', '')):
        if img.get('status') == 'active' and img['name'] not in seen:
            if any(x in img['name'].lower() for x in ['ubuntu', 'debian', 'rocky', 'centos', 'alma']):
                seen.add(img['name'])
                result.append({
                    'name': img['name'],
                    'id': img['id'],
                    'desc': img.get('type', '')
                })
    return result

def add_instance():
    """Wizard per aggiungere una VM"""

    # Nome
    clear()
    print("=" * 60)
    print(" NUOVA ISTANZA VM")
    print("=" * 60)
    print()
    name = input_text("Nome della VM", "test-vm")
    if not name:
        return

    # Categoria flavor
    categories = get_flavor_categories()
    cat_options = [{'name': k, 'desc': v} for k, v in categories.items()]
    category = menu("SCEGLI CATEGORIA", cat_options)
    if not category:
        return

    # Flavor della categoria
    flavors = get_flavors(category_prefix=category['name'])
    if not flavors:
        print("Nessun flavor disponibile in questa categoria!")
        input("Premi INVIO...")
        return

    flavor = menu(f"SCEGLI FLAVOR ({category['name'].upper()})", flavors)
    if not flavor:
        return

    # Immagine
    images = get_images()
    if not images:
        print("Nessuna immagine disponibile!")
        input("Premi INVIO...")
        return

    image = menu("SCEGLI SISTEMA OPERATIVO", images)
    if not image:
        return

    # IP pubblico?
    clear()
    print("=" * 60)
    print(" IP PUBBLICO")
    print("=" * 60)
    print()
    public_ip = input_text("Vuoi un IP pubblico? (s/n)", "s").lower() == 's'

    # Rete privata?
    private_net = input_text("Collegare alla rete privata? (s/n)", "s").lower() == 's'

    # Genera resource name (terraform-safe)
    resource_name = name.replace("-", "_").replace(" ", "_").lower()

    # Genera HCL con nuova sintassi
    hcl = f'''
# -----------------------------------------------------------------------------
# Istanza: {name}
# -----------------------------------------------------------------------------

resource "ovh_cloud_project_instance" "{resource_name}" {{
  service_name   = var.service_name
  name           = "{name}"
  region         = var.region
  billing_period = "hourly"

  boot_from {{
    image_id = "{image['id']}"  # {image['name']}
  }}

  flavor {{
    flavor_id = "{flavor['id']}"  # {flavor['name']}
  }}

  ssh_key {{
    name = ovh_cloud_project_ssh_key.main.name
  }}

  network {{
    public = {str(public_ip).lower()}
  }}
}}
'''

    # Output
    output_hcl = f'''
output "{resource_name}_ip" {{
  description = "IP della VM {name}"
  value       = ovh_cloud_project_instance.{resource_name}.addresses
}}
'''

    # Preview
    clear()
    print("=" * 60)
    print(" ANTEPRIMA")
    print("=" * 60)
    print(hcl)
    print()
    confirm = input_text("Aggiungere a main.tf? (s/n)", "s")

    if confirm.lower() == 's':
        with open(MAIN_TF, 'a') as f:
            f.write(hcl)

        # Aggiungi output
        with open("/root/digitalocean/OVH/outputs.tf", 'a') as f:
            f.write(output_hcl)

        print()
        print("Aggiunto a main.tf!")
        print()
        print("Ora esegui:")
        print("  terraform plan    # Vedi cosa crea")
        print("  terraform apply   # Crea la VM")
        print()
    else:
        print("Annullato")

    input("Premi INVIO...")

def add_volume():
    """Wizard per aggiungere un volume"""
    clear()
    print("=" * 60)
    print(" NUOVO VOLUME (DISCO)")
    print("=" * 60)
    print()

    name = input_text("Nome del volume", "data-volume")
    if not name:
        return

    size = input_text("Dimensione in GB", "20")

    resource_name = name.replace("-", "_").replace(" ", "_").lower()

    hcl = f'''
# -----------------------------------------------------------------------------
# Volume: {name}
# -----------------------------------------------------------------------------

resource "ovh_cloud_project_volume" "{resource_name}" {{
  service_name = var.service_name
  name         = "{name}"
  region       = var.region
  size         = {size}
  type         = "high-speed"
}}
'''

    clear()
    print("=" * 60)
    print(" ANTEPRIMA")
    print("=" * 60)
    print(hcl)
    print()
    confirm = input_text("Aggiungere a main.tf? (s/n)", "s")

    if confirm.lower() == 's':
        with open(MAIN_TF, 'a') as f:
            f.write(hcl)
        print()
        print("Aggiunto a main.tf!")
        print("Ora esegui: terraform plan && terraform apply")
        print()
    else:
        print("Annullato")

    input("Premi INVIO...")

def main_menu():
    """Menu principale"""
    while True:
        choice = menu("AGGIUNGI RISORSA OVH", [
            {'name': 'Istanza (VM)', 'desc': 'Virtual machine'},
            {'name': 'Volume', 'desc': 'Disco aggiuntivo'},
            {'name': 'Esci', 'desc': ''},
        ])

        if not choice or choice['name'] == 'Esci':
            clear()
            print("Ciao!")
            break
        elif choice['name'] == 'Istanza (VM)':
            add_instance()
        elif choice['name'] == 'Volume':
            add_volume()

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nInterrotto")
