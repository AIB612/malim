# Malim Infrastructure

## Prerequisites

1. Azure CLI installed and logged in
2. Terraform >= 1.5.0
3. Docker

## Quick Start

```bash
# 1. Initialize Terraform
cd infra
terraform init

# 2. Create infrastructure
terraform plan -var="db_admin_password=YourSecurePassword123!"
terraform apply -var="db_admin_password=YourSecurePassword123!"

# 3. Deploy application
cd ..
./scripts/deploy.sh dev
```

## Resources Created

| Resource | Type | Purpose |
|----------|------|---------|
| rg-malim-dev | Resource Group | Container for all resources |
| acrmalimdev | Container Registry | Docker images |
| psql-malim-dev | PostgreSQL Flexible | Database + pgvector |
| cae-malim-dev | Container Apps Env | Serverless hosting |
| ca-malim-api-dev | Container App | API service |

## Costs (Switzerland North)

Estimated monthly costs for dev environment:

| Resource | SKU | Est. Cost |
|----------|-----|-----------|
| PostgreSQL | B_Standard_B1ms | ~CHF 15/mo |
| Container Apps | Consumption | ~CHF 0-10/mo |
| Container Registry | Basic | ~CHF 5/mo |
| **Total** | | **~CHF 20-30/mo** |

## Production Setup

For production, consider:

1. Enable Azure AI Search for better RAG:
   ```bash
   terraform apply -var="enable_azure_search=true"
   ```

2. Use Standard PostgreSQL tier for better performance

3. Enable Azure OpenAI in Switzerland North (when available)

## Environment Variables

Set these in Container App:

| Variable | Description |
|----------|-------------|
| POSTGRES_HOST | PostgreSQL FQDN |
| POSTGRES_DB | Database name |
| POSTGRES_USER | Admin username |
| POSTGRES_PASSWORD | Admin password |
| VECTOR_STORE | "pgvector" or "azure" |
| AZURE_OPENAI_ENDPOINT | Azure OpenAI endpoint |
| AZURE_OPENAI_KEY | Azure OpenAI key |

## Cleanup

```bash
terraform destroy -var="db_admin_password=xxx"
```
