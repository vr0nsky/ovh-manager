# =============================================================================
# VARIABILI OVH
# =============================================================================

variable "ovh_endpoint" {
  description = "Endpoint API OVH (ovh-eu, ovh-ca, ovh-us)"
  type        = string
  default     = "ovh-eu"
}

variable "service_name" {
  description = "ID del progetto Public Cloud OVH (lo trovi nel pannello OVH)"
  type        = string
}

# =============================================================================
# VARIABILI INFRASTRUTTURA
# =============================================================================

variable "region" {
  description = "Regione OVH (GRA7, SBG5, DE1, UK1, BHS5, WAW1, etc.)"
  type        = string
  default     = "GRA7"
}

variable "environment" {
  description = "Nome ambiente (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Nome del progetto per i tag"
  type        = string
  default     = "myproject"
}
