# ADLS Gen2 storage account for insurance lakehouse (production stub)
# Creates bronze/silver/gold containers with hierarchical namespace enabled.
# Not executed in CI — run `terraform apply` with Azure credentials to provision.

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }
}

variable "resource_group_name" { type = string }
variable "location"            { type = string   default = "westeurope" }
variable "storage_account_name" { type = string }

resource "azurerm_storage_account" "lakehouse" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true  # hierarchical namespace (ADLS Gen2)
}

resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.lakehouse.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.lakehouse.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.lakehouse.name
  container_access_type = "private"
}

output "storage_account_id"   { value = azurerm_storage_account.lakehouse.id }
output "primary_dfs_endpoint" { value = azurerm_storage_account.lakehouse.primary_dfs_endpoint }
