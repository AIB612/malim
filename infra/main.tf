# Azure Infrastructure for Malim
# Deploy to Switzerland North for data compliance

# Resource Group
resource "azurerm_resource_group" "malim" {
  name     = "rg-malim-${var.environment}"
  location = "switzerlandnorth"
  
  tags = {
    project     = "malim"
    environment = var.environment
  }
}

# Container Registry
resource "azurerm_container_registry" "malim" {
  name                = "acrmalim${var.environment}"
  resource_group_name = azurerm_resource_group.malim.name
  location            = azurerm_resource_group.malim.location
  sku                 = "Basic"
  admin_enabled       = true
}

# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "malim" {
  name                   = "psql-malim-${var.environment}"
  resource_group_name    = azurerm_resource_group.malim.name
  location               = azurerm_resource_group.malim.location
  version                = "16"
  administrator_login    = var.db_admin_user
  administrator_password = var.db_admin_password
  
  storage_mb = 32768
  sku_name   = "B_Standard_B1ms"  # Burstable, cost-effective
  
  zone = "1"
  
  tags = {
    project = "malim"
  }
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "malim" {
  name      = "malim"
  server_id = azurerm_postgresql_flexible_server.malim.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Enable pgvector extension
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.malim.id
  value     = "vector"
}

# Container Apps Environment
resource "azurerm_container_app_environment" "malim" {
  name                = "cae-malim-${var.environment}"
  location            = azurerm_resource_group.malim.location
  resource_group_name = azurerm_resource_group.malim.name
}

# Container App - API
resource "azurerm_container_app" "api" {
  name                         = "ca-malim-api-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.malim.id
  resource_group_name          = azurerm_resource_group.malim.name
  revision_mode                = "Single"
  
  template {
    container {
      name   = "malim-api"
      image  = "${azurerm_container_registry.malim.login_server}/malim:latest"
      cpu    = 0.5
      memory = "1Gi"
      
      env {
        name  = "APP_ENV"
        value = var.environment
      }
      
      env {
        name  = "POSTGRES_HOST"
        value = azurerm_postgresql_flexible_server.malim.fqdn
      }
      
      env {
        name  = "POSTGRES_DB"
        value = "malim"
      }
      
      env {
        name        = "POSTGRES_USER"
        secret_name = "db-user"
      }
      
      env {
        name        = "POSTGRES_PASSWORD"
        secret_name = "db-password"
      }
      
      env {
        name  = "VECTOR_STORE"
        value = "pgvector"
      }
    }
    
    min_replicas = 0
    max_replicas = 3
  }
  
  ingress {
    external_enabled = true
    target_port      = 8000
    
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
  
  secret {
    name  = "db-user"
    value = var.db_admin_user
  }
  
  secret {
    name  = "db-password"
    value = var.db_admin_password
  }
  
  registry {
    server               = azurerm_container_registry.malim.login_server
    username             = azurerm_container_registry.malim.admin_username
    password_secret_name = "acr-password"
  }
  
  secret {
    name  = "acr-password"
    value = azurerm_container_registry.malim.admin_password
  }
}

# Azure AI Search (optional, for production RAG)
resource "azurerm_search_service" "malim" {
  count               = var.enable_azure_search ? 1 : 0
  name                = "search-malim-${var.environment}"
  resource_group_name = azurerm_resource_group.malim.name
  location            = azurerm_resource_group.malim.location
  sku                 = "basic"
  
  tags = {
    project = "malim"
  }
}

# Outputs
output "api_url" {
  value = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "acr_login_server" {
  value = azurerm_container_registry.malim.login_server
}

output "postgres_host" {
  value = azurerm_postgresql_flexible_server.malim.fqdn
}
