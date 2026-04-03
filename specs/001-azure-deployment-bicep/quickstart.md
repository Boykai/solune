# Quick Start: Solune Azure Deployment

**Date**: 2026-04-03 | **Plan**: [plan.md](./plan.md)

## Prerequisites

- **Azure subscription** with permissions to create resources (Contributor + User Access Administrator at subscription level)
- **GitHub OAuth App** — create at [github.com/settings/developers](https://github.com/settings/developers)
  - Homepage URL: `https://<your-frontend-fqdn>` (update after deployment)
  - Callback URL: `https://<your-frontend-fqdn>/api/v1/auth/github/callback` (update after deployment)
- **Azure CLI** (`az`) v2.60+ — [Install](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Azure Developer CLI** (`azd`) v1.9+ — [Install](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- **Bicep CLI** (included with Azure CLI v2.60+)

## Option 1: Deploy to Azure Button (One-Click)

1. Click the **Deploy to Azure** button in the [README](../../README.md)
2. Fill in the deployment form:
   - **Environment Name**: Choose a unique name (e.g., `solune-prod`)
   - **Location**: Select an Azure region (e.g., `East US 2`)
   - **GitHub Client ID**: From your GitHub OAuth App
   - **GitHub Client Secret**: From your GitHub OAuth App
   - **Session Secret Key**: Generate with `openssl rand -hex 32`
   - **Encryption Key**: Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   - **Admin GitHub User ID**: Your numeric GitHub user ID
3. Click **Review + Create** → **Create**
4. Wait ~10 minutes for all resources to provision
5. After deployment, get the frontend URL from the outputs
6. **Update GitHub OAuth App** callback URL to: `https://<frontend-fqdn>/api/v1/auth/github/callback`

## Option 2: Azure Developer CLI (`azd up`)

```bash
# Clone the repository
git clone https://github.com/Boykai/solune.git
cd solune

# Login to Azure
az login
azd auth login

# Initialize environment
azd init -e solune-prod

# Set required parameters
azd env set GITHUB_CLIENT_ID <your-client-id>
azd env set GITHUB_CLIENT_SECRET <your-client-secret>
azd env set SESSION_SECRET_KEY $(openssl rand -hex 32)
azd env set ENCRYPTION_KEY $(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
azd env set ADMIN_GITHUB_USER_ID <your-github-user-id>

# Deploy everything (provision infra + build + deploy)
azd up
```

## Option 3: Manual Bicep Deployment

```bash
# Login
az login
az account set --subscription <subscription-id>

# Create resource group
az group create --name rg-solune-prod --location eastus2

# Deploy infrastructure
az deployment group create \
  --resource-group rg-solune-prod \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam \
  --parameters githubClientId=<id> \
  --parameters githubClientSecret=<secret> \
  --parameters sessionSecretKey=$(openssl rand -hex 32) \
  --parameters encryptionKey=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
  --parameters adminGitHubUserId=<user-id>

# Build and push images
az acr build --registry <acr-name> --image solune-backend:latest ./solune/backend
az acr build --registry <acr-name> --image solune-frontend:latest ./solune/frontend

# Update container apps with new images
az containerapp update --name ca-backend-solune-prod --resource-group rg-solune-prod \
  --image <acr-name>.azurecr.io/solune-backend:latest
az containerapp update --name ca-frontend-solune-prod --resource-group rg-solune-prod \
  --image <acr-name>.azurecr.io/solune-frontend:latest
```

## Post-Deployment Configuration

### 1. Update GitHub OAuth App

After deployment, update your GitHub OAuth App settings:
- **Homepage URL**: `https://<frontend-fqdn>`
- **Authorization callback URL**: `https://<frontend-fqdn>/api/v1/auth/github/callback`

Get the frontend URL:
```bash
# Via azd
azd env get-values | grep FRONTEND_URL

# Via Azure CLI
az containerapp show --name ca-frontend-solune-prod --resource-group rg-solune-prod \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

### 2. Verify Deployment

```bash
# Check all container apps are running
az containerapp list --resource-group rg-solune-prod -o table

# Check backend health
curl https://<backend-internal-fqdn>/api/v1/health

# Check frontend health (external)
curl https://<frontend-fqdn>/health

# Check Key Vault secrets
az keyvault secret list --vault-name kv-solune-prod -o table

# Verify no secrets in container env vars
az containerapp show --name ca-backend-solune-prod --resource-group rg-solune-prod \
  --query "properties.template.containers[0].env" -o table
```

### 3. Verify AI Integration

```bash
# Check Azure OpenAI deployment
az cognitiveservices account deployment list \
  --name oai-solune-prod \
  --resource-group rg-solune-prod -o table

# Check backend logs for OpenAI connections
az containerapp logs show --name ca-backend-solune-prod \
  --resource-group rg-solune-prod --tail 50
```

## Validation Commands

```bash
# Lint Bicep files
az bicep lint --file infra/main.bicep

# Preview deployment (what-if)
az deployment group what-if \
  --resource-group rg-solune-prod \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam

# azd preview
azd provision --preview
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Deploy button fails | Check ARM template URL is accessible; ensure `azuredeploy.json` is committed |
| Container App won't start | Check `az containerapp logs show`; verify ACR image exists |
| Key Vault access denied | Verify managed identity has `Key Vault Secrets User` role |
| OpenAI 403 error | Verify managed identity has `Cognitive Services OpenAI User` role |
| OAuth callback error | Update GitHub OAuth App callback URL to match frontend FQDN |
| SQLite lock errors | Verify Azure Files share is mounted with ReadWrite access |
| Signal API unreachable | Check signal-api Container App is running with internal ingress |
