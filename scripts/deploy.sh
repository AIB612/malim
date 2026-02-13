#!/bin/bash
# Deploy Malim to Azure
# Usage: ./deploy.sh [dev|staging|prod]

set -e

ENV=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying Malim to Azure ($ENV)"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Install: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Check login
if ! az account show &> /dev/null; then
    echo "🔐 Please login to Azure..."
    az login
fi

# Get ACR credentials
ACR_NAME="acrmalim${ENV}"
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv 2>/dev/null || echo "")

if [ -z "$ACR_LOGIN_SERVER" ]; then
    echo "⚠️ ACR not found. Run Terraform first:"
    echo "   cd infra && terraform apply"
    exit 1
fi

# Login to ACR
echo "🔑 Logging into ACR..."
az acr login --name $ACR_NAME

# Build and push image
echo "🐳 Building Docker image..."
cd "$ROOT_DIR"
docker build -t malim:latest .
docker tag malim:latest $ACR_LOGIN_SERVER/malim:latest
docker push $ACR_LOGIN_SERVER/malim:latest

# Update Container App
echo "🔄 Updating Container App..."
az containerapp update \
    --name "ca-malim-api-${ENV}" \
    --resource-group "rg-malim-${ENV}" \
    --image "$ACR_LOGIN_SERVER/malim:latest"

# Get API URL
API_URL=$(az containerapp show \
    --name "ca-malim-api-${ENV}" \
    --resource-group "rg-malim-${ENV}" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "✅ Deployment complete!"
echo "🌐 API URL: https://$API_URL"
echo "📚 Docs: https://$API_URL/docs"
