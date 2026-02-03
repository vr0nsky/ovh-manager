# =============================================================================
# RISORSE OVH PUBLIC CLOUD
# =============================================================================

# -----------------------------------------------------------------------------
# Data Sources - Info sul progetto
# -----------------------------------------------------------------------------

# Info sul progetto Public Cloud
data "ovh_cloud_project" "project" {
  service_name = var.service_name
}

# Lista delle regioni disponibili
data "ovh_cloud_project_regions" "regions" {
  service_name = var.service_name
}

# -----------------------------------------------------------------------------
# Network - Rete privata
# -----------------------------------------------------------------------------

# Rete privata (vRack network)
resource "ovh_cloud_project_network_private" "private_network" {
  service_name = var.service_name
  name         = "${var.project_name}-${var.environment}-network"
  regions      = [var.region]
  vlan_id      = 100
}

# Subnet nella rete privata
resource "ovh_cloud_project_network_private_subnet" "subnet" {
  service_name = var.service_name
  network_id   = ovh_cloud_project_network_private.private_network.id
  region       = var.region
  start        = "192.168.1.10"
  end          = "192.168.1.200"
  network      = "192.168.1.0/24"
  dhcp         = true
  no_gateway   = false
}

# -----------------------------------------------------------------------------
# SSH Key
# -----------------------------------------------------------------------------

resource "ovh_cloud_project_ssh_key" "main" {
  service_name = var.service_name
  name         = "${var.project_name}-${var.environment}-key"
  public_key   = file("/root/.ssh/id_ed25519.pub")
  region       = var.region
}
