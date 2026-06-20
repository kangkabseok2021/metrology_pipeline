# Terraform — Production Target Architecture

These stubs document the ADLS Gen2 + Azure Databricks infrastructure for the production lakehouse.
They are **not executed in CI** (no Azure subscription required to run tests).

## Modules

| Module | What it provisions |
|---|---|
| `adls_gen2` | Storage account with HNS + bronze/silver/gold containers |
| `databricks_workspace` | Azure Databricks workspace + Repos integration + per-layer jobs |

## Running (requires Azure credentials)

```bash
terraform -chdir=modules/adls_gen2 init
terraform -chdir=modules/adls_gen2 apply \
  -var="resource_group_name=rg-insurance-lakehouse" \
  -var="storage_account_name=stinsurancelh001"
```
