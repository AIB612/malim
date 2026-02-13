# Terraform Variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "db_admin_user" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "malimadmin"
}

variable "db_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "enable_azure_search" {
  description = "Enable Azure AI Search for production RAG"
  type        = bool
  default     = false
}
