# Feature Specification: Solune Azure Deployment with Bicep IaC

**Branch**: `001-azure-deployment-bicep` | **Date**: 2026-04-03 | **Issue**: #632

## Overview

Deploy Solune (FastAPI backend + React/nginx frontend + Signal sidecar) to Azure using Bicep IaC with a single-click "Deploy to Azure" button. Uses Azure Container Apps, Azure OpenAI, Azure AI Foundry, Azure Key Vault, managed identity, and an azd template — no hardcoded secrets.

## User Stories

### P1: One-Click Azure Deployment

**As a** developer or team lead,
**I want to** click a "Deploy to Azure" button in the README,
**So that** I can provision the full Solune stack on Azure without manual infrastructure setup.

**Acceptance Criteria:**
- Given the README has a "Deploy to Azure" button, when I click it, then the Azure Portal opens with a custom deployment form
- Given I fill in required parameters (GitHub OAuth, admin user ID), when I click "Create", then all Azure resources are provisioned
- Given deployment completes, when I visit the frontend FQDN, then I see the Solune login page
- Independent Test: `az deployment sub what-if` with test parameters validates the ARM template

### P1: Secure Secret Management

**As a** platform operator,
**I want** all secrets stored in Azure Key Vault with managed identity access,
**So that** no API keys or secrets appear in container environment variables.

**Acceptance Criteria:**
- Given deployment completes, when I inspect container env vars, then no secrets are present — only Key Vault references
- Given the backend starts, when it reads secrets, then it uses managed identity to access Key Vault
- Independent Test: `az keyvault secret list` confirms secrets exist; container env shows only references

### P1: Azure OpenAI Integration

**As a** user,
**I want** the Azure deployment to use Azure OpenAI (not Copilot SDK),
**So that** AI features work reliably in production without requiring user OAuth tokens.

**Acceptance Criteria:**
- Given AI_PROVIDER=azure_openai is configured, when I use AI generation features, then requests go to Azure OpenAI
- Given managed identity is configured, when the backend calls Azure OpenAI, then it authenticates via managed identity (Cognitive Services OpenAI User role)
- Independent Test: Backend logs show successful Azure OpenAI connections

### P2: Infrastructure as Code with Bicep Modules

**As a** DevOps engineer,
**I want** modular Bicep files for each Azure service,
**So that** I can understand, modify, and maintain individual infrastructure components.

**Acceptance Criteria:**
- Given the infra/ directory, when I inspect it, then each Azure service has its own Bicep module
- Given I run `az bicep lint`, when it completes, then there are no errors
- Independent Test: `az bicep lint --file infra/main.bicep` passes clean

### P2: azd Template Support

**As a** developer,
**I want** an azd-compatible project structure,
**So that** I can use `azd up` as an alternative to the deploy button.

**Acceptance Criteria:**
- Given azure.yaml exists at project root, when I run `azd up`, then all three services build and deploy
- Independent Test: `azd provision --preview` shows expected resources

### P3: CI/CD Pipeline (Optional)

**As a** team,
**I want** a GitHub Actions workflow for automated Azure deployments,
**So that** pushes to main automatically update the Azure environment.

**Acceptance Criteria:**
- Given the workflow exists, when I push to main, then azd provision + deploy runs automatically
- Given OIDC credentials are configured, when the workflow authenticates, then no static secrets are stored in GitHub

## Scope

### In Scope
- Azure Container Apps for all 3 services (backend, frontend, signal-api)
- Azure OpenAI with gpt-4o deployment
- Azure AI Foundry hub + project
- Azure Key Vault for secret management
- Azure Container Registry for images
- Azure Storage (Azure Files) for SQLite persistence and Signal config
- Log Analytics + Application Insights for monitoring
- Single user-assigned managed identity with all required RBAC roles
- Deploy to Azure button (compiled ARM JSON)
- azd template (azure.yaml)
- README updates
- Optional CI/CD workflow

### Out of Scope
- Custom domain + SSL (can be added later as optional Bicep parameters)
- Azure SQL or Cosmos DB migration (keeping SQLite on Azure Files)
- VNet peering or custom networking (using managed VNet)
- Multi-region deployment
- Azure Front Door / CDN

## Decisions

| Decision | Rationale |
|----------|-----------|
| AI_PROVIDER=azure_openai | More reliable for production than Copilot SDK which needs user OAuth tokens |
| SQLite on Azure Files | Simplest persistence for current arch; matches existing docker-compose volume pattern |
| Signal as separate Container App | Mirrors docker-compose sidecar pattern with internal ingress |
| Single user-assigned managed identity | Sufficient at this scale; simpler than per-service identities |
| Managed VNet (no custom VNet) | Container Apps built-in networking for internal service communication |
| ARM JSON for deploy button | Azure portal requires compiled ARM, not raw Bicep |
