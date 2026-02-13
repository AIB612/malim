terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
  
  # Uncomment for remote state
  # backend "azurerm" {
  #   resource_group_name  = "rg-terraform-state"
  #   storage_account_name = "stmalimtfstate"
  #   container_name       = "tfstate"
  #   key                  = "malim.tfstate"
  # }
}

provider "azurerm" {
  features {}
}
