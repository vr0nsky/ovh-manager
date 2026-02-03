# =============================================================================
# OUTPUT
# =============================================================================

output "project_info" {
  description = "Info sul progetto Public Cloud"
  value = {
    id          = data.ovh_cloud_project.project.project_id
    description = data.ovh_cloud_project.project.description
    status      = data.ovh_cloud_project.project.status
  }
}

output "available_regions" {
  description = "Regioni disponibili per il progetto"
  value       = data.ovh_cloud_project_regions.regions.names
}

output "private_network" {
  description = "Info sulla rete privata"
  value = {
    id      = ovh_cloud_project_network_private.private_network.id
    name    = ovh_cloud_project_network_private.private_network.name
    vlan_id = ovh_cloud_project_network_private.private_network.vlan_id
  }
}

output "subnet" {
  description = "Info sulla subnet"
  value = {
    id      = ovh_cloud_project_network_private_subnet.subnet.id
    cidr    = ovh_cloud_project_network_private_subnet.subnet.network
    gateway = ovh_cloud_project_network_private_subnet.subnet.gateway_ip
  }
}

output "ssh_key" {
  description = "SSH key registrata"
  value = {
    name        = ovh_cloud_project_ssh_key.main.name
    finger_print = ovh_cloud_project_ssh_key.main.finger_print
  }
}

# Output per istanze (decommentare quando attive)
# output "web_instance" {
#   description = "Info istanza web"
#   value = {
#     id         = ovh_cloud_project_instance.web.id
#     name       = ovh_cloud_project_instance.web.name
#     public_ip  = ovh_cloud_project_instance.web.addresses[0].ip
#     private_ip = ovh_cloud_project_instance.web.addresses[1].ip
#   }
# }





