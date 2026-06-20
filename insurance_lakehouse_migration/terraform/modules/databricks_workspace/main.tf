# Azure Databricks workspace + per-layer job definitions (production stub).
# Notebooks are deployed via Databricks Repos pointing to the GitHub source.

terraform {
  required_providers {
    azurerm    = { source = "hashicorp/azurerm"    version = "~> 3.90" }
    databricks = { source = "databricks/databricks" version = "~> 1.40" }
  }
}

variable "resource_group_name" { type = string }
variable "location"            { type = string   default = "westeurope" }
variable "workspace_name"      { type = string }
variable "github_repo_url"     { type = string   default = "https://github.com/kangkabseok2021/metrology_pipeline" }

resource "azurerm_databricks_workspace" "insurance" {
  name                = var.workspace_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "premium"
}

resource "databricks_repo" "pipeline" {
  url    = var.github_repo_url
  path   = "/Repos/insurance_lakehouse_migration"
}

resource "databricks_job" "bronze_ingestion" {
  name = "insurance-bronze-ingestion"
  task {
    task_key = "extract_all"
    notebook_task {
      notebook_path = "${databricks_repo.pipeline.path}/insurance_lakehouse_migration/pipeline/bronze/extract.py"
    }
  }
}

resource "databricks_job" "silver_transform" {
  name = "insurance-silver-transform"
  task {
    task_key = "silver"
    depends_on { task_key = "extract_all" }
    notebook_task {
      notebook_path = "${databricks_repo.pipeline.path}/insurance_lakehouse_migration/pipeline/silver/transforms.py"
    }
  }
  depends_on = [databricks_job.bronze_ingestion]
}

output "workspace_url" { value = azurerm_databricks_workspace.insurance.workspace_url }
