#!/bin/bash
# =============================================================================
# SETUP CREDENZIALI OVH
# =============================================================================
# Esegui: source setup.sh

echo "=== CONFIGURAZIONE OVH TERRAFORM ==="
echo ""
echo "1. Vai su: https://www.ovh.com/auth/api/createToken"
echo ""
echo "2. Compila il form:"
echo "   - Application name: terraform"
echo "   - Application description: Terraform automation"
echo "   - Validity: Unlimited"
echo "   - Rights: (vedi sotto)"
echo ""
echo "3. Rights necessari (aggiungi tutte queste righe):"
echo "   GET    /*"
echo "   POST   /*"
echo "   PUT    /*"
echo "   DELETE /*"
echo ""
echo "4. Copia le chiavi generate e incollale qui sotto:"
echo ""

read -p "OVH_APPLICATION_KEY: " app_key
read -p "OVH_APPLICATION_SECRET: " app_secret
read -p "OVH_CONSUMER_KEY: " consumer_key

echo ""
echo "5. Trova il tuo Project ID:"
echo "   OVH Manager > Public Cloud > Il tuo progetto > Project Settings"
echo "   (è una stringa tipo: abc123def456789...)"
echo ""
read -p "PROJECT_ID (service_name): " project_id

# Crea file di configurazione
cat > ~/.ovh.conf << EOF
[default]
endpoint=ovh-eu

[ovh-eu]
application_key=${app_key}
application_secret=${app_secret}
consumer_key=${consumer_key}
EOF

chmod 600 ~/.ovh.conf

# Crea terraform.tfvars
cat > terraform.tfvars << EOF
service_name = "${project_id}"
region       = "GRA7"
environment  = "dev"
project_name = "myproject"
EOF

echo ""
echo "=== CONFIGURAZIONE COMPLETATA ==="
echo ""
echo "File creati:"
echo "  - ~/.ovh.conf (credenziali)"
echo "  - terraform.tfvars (configurazione)"
echo ""
echo "Ora puoi eseguire:"
echo "  terraform init"
echo "  terraform plan"
echo ""
