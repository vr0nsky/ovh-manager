#!/usr/bin/env python3
"""
Rimuove risorse dal file Terraform
"""

import os
import sys
import hcl2

MAIN_TF = "/root/digitalocean/OVH/main.tf"
OUTPUTS_TF = "/root/digitalocean/OVH/outputs.tf"

def clear():
    os.system('clear')

def get_resources():
    """Trova risorse con hcl2"""
    with open(MAIN_TF, 'r') as f:
        parsed = hcl2.load(f)

    resources = []
    for res_block in parsed.get('resource', []):
        for res_type, instances in res_block.items():
            for res_name in instances.keys():
                resources.append((res_type, res_name))
    return resources

def remove_resource(res_type, res_name):
    """Rimuove la risorsa dal file"""
    with open(MAIN_TF, 'r') as f:
        lines = f.readlines()

    # Trova la riga della risorsa
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('resource "'):
            if f'"{res_type}"' in line and f'"{res_name}"' in line:
                start = i
                break

    if start is None:
        print(f"Errore: risorsa non trovata nel file")
        return False

    # Includi commenti sopra
    while start > 0 and (lines[start-1].strip().startswith('#') or lines[start-1].strip() == ''):
        start -= 1

    # Trova la fine contando { }
    braces = 0
    end = start
    started = False
    for i in range(start, len(lines)):
        braces += lines[i].count('{') - lines[i].count('}')
        if '{' in lines[i]:
            started = True
        if started and braces == 0:
            end = i
            break

    # Rimuovi
    del lines[start:end+1]

    # Scrivi
    with open(MAIN_TF, 'w') as f:
        f.writelines(lines)

    return True

def remove_output(res_name):
    """Rimuove output associato"""
    if not os.path.exists(OUTPUTS_TF):
        return

    with open(OUTPUTS_TF, 'r') as f:
        lines = f.readlines()

    marker = f'output "{res_name}_ip"'
    start = None
    for i, line in enumerate(lines):
        if marker in line:
            start = i
            break

    if start is None:
        return

    braces = 0
    end = start
    started = False
    for i in range(start, len(lines)):
        braces += lines[i].count('{') - lines[i].count('}')
        if '{' in lines[i]:
            started = True
        if started and braces == 0:
            end = i
            break

    del lines[start:end+1]

    with open(OUTPUTS_TF, 'w') as f:
        f.writelines(lines)

    print(f"  Rimosso anche output \"{res_name}_ip\"")

def main():
    clear()
    print("=" * 50)
    print(" RIMUOVI RISORSA")
    print("=" * 50)
    print()

    resources = get_resources()

    if not resources:
        print("Nessuna risorsa trovata")
        return

    for i, (rtype, rname) in enumerate(resources, 1):
        print(f"  {i}. {rtype}.{rname}")

    print()
    print("  0. Esci")
    print()

    try:
        n = input("Numero: ").strip()
        if n == '0' or n == '':
            return

        idx = int(n) - 1
        if idx < 0 or idx >= len(resources):
            print("Numero non valido")
            return

        res_type, res_name = resources[idx]

        print()
        print(f"Rimuovo: {res_type}.{res_name}")
        print()

        ok = input("Sicuro? (si/no): ").strip().lower()

        if ok not in ('si', 's', 'yes', 'y'):
            print("Annullato")
            return

        if remove_resource(res_type, res_name):
            print()
            print(f"  Rimosso {res_type}.{res_name}")
            remove_output(res_name)
            print()
            print("Fatto! Verifica con: terraform plan")

    except ValueError:
        print("Input non valido")
    except KeyboardInterrupt:
        print("\nAnnullato")

if __name__ == "__main__":
    main()
