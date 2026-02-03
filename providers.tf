# Provider OVH
# Autenticazione via variabili d'ambiente:
#   OVH_ENDPOINT           = "ovh-eu"
#   OVH_APPLICATION_KEY    = "xxx"
#   OVH_APPLICATION_SECRET = "yyy"
#   OVH_CONSUMER_KEY       = "zzz"

provider "ovh" {
  endpoint = var.ovh_endpoint
  # Le credenziali vengono lette dalle variabili d'ambiente
}
