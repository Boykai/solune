# Data Model: Solune Azure Deployment with Bicep IaC

**Date**: 2026-04-03 | **Plan**: [plan.md](./plan.md)

## Overview

This data model describes the Azure resource graph — entities (Azure resources), their fields (Bicep properties), relationships (dependencies and references), and state transitions (deployment lifecycle). This is an IaC feature with no application data model changes.

## Entity Diagram (Resource Graph)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Resource Group (rg-{env})                           │
│                                                                              │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────────────┐  │
│  │ User-Assigned    │    │ Log Analytics     │    │ Application Insights   │  │
│  │ Managed Identity │    │ Workspace         │───▶│ (connected to LAW)     │  │
│  │                  │    └──────┬───────────┘    └────────────────────────┘  │
│  └──────┬───────────┘           │                                            │
│         │ (RBAC roles)          │ (diagnostics)                              │
│         │                       │                                            │
│  ┌──────▼───────────┐    ┌──────▼───────────┐    ┌────────────────────────┐  │
│  │ Container         │    │ Key Vault         │    │ Storage Account        │  │
│  │ Registry (ACR)    │    │ (RBAC auth)       │    │ + File Shares          │  │
│  │ [AcrPull]         │    │ [KV Secrets User] │    │ [Storage SMB Contrib]  │  │
│  └──────┬───────────┘    └──────┬───────────┘    └──────┬─────────────────┘  │
│         │                       │                       │                     │
│         │ (image pull)          │ (secret refs)         │ (volume mounts)     │
│         ▼                       ▼                       ▼                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │               Container Apps Environment (managed VNet)                 │  │
│  │                                                                         │  │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐    │  │
│  │  │ frontend     │   │ backend      │   │ signal-api               │    │  │
│  │  │ (external)   │──▶│ (internal)   │──▶│ (internal)               │    │  │
│  │  │ :8080        │   │ :8000        │   │ :8080                    │    │  │
│  │  │ nginx+React  │   │ FastAPI      │   │ signal-cli-rest-api      │    │  │
│  │  └──────────────┘   └──────┬───────┘   └──────────────────────────┘    │  │
│  │                            │                                            │  │
│  └────────────────────────────┼────────────────────────────────────────────┘  │
│                               │                                              │
│  ┌────────────────────────────▼─────────────────────────────────────────┐    │
│  │                    AI Services                                        │    │
│  │  ┌──────────────────┐   ┌───────────────────────────────────────┐    │    │
│  │  │ Azure OpenAI     │   │ AI Foundry                            │    │    │
│  │  │ + gpt-4o deploy  │   │ Hub + Project                         │    │    │
│  │  │ [Cog Svc User]   │   │ [AI Developer]                        │    │    │
│  │  └──────────────────┘   └───────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Entities

### 1. User-Assigned Managed Identity

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.ManagedIdentity/userAssignedIdentities` |  |
| **Name** | `id-{environmentName}` |  |
| **Location** | `{location}` parameter |  |
| **Tags** | `azd-env-name: {environmentName}` |  |

**Relationships**: Assigned to backend Container App. RBAC role assignments on ACR, Key Vault, OpenAI, AI Foundry, Storage.

### 2. Log Analytics Workspace

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.OperationalInsights/workspaces` |  |
| **Name** | `law-{environmentName}` |  |
| **SKU** | `PerGB2018` | Pay-as-you-go |
| **Retention** | 30 days |  |

**Relationships**: Connected to Application Insights, Container Apps Environment, AI Foundry Hub.

### 3. Application Insights

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.Insights/components` |  |
| **Name** | `ai-{environmentName}` |  |
| **Kind** | `web` |  |
| **Application Type** | `web` |  |
| **Workspace** | → Log Analytics Workspace |  |

### 4. Container Registry (ACR)

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.ContainerRegistry/registries` |  |
| **Name** | `{environmentName}acr` | Globally unique, alphanumeric only |
| **SKU** | `Basic` |  |
| **Admin** | `false` | Managed identity only |

**Relationships**: AcrPull role → Managed Identity.

### 5. Key Vault

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.KeyVault/vaults` |  |
| **Name** | `kv-{environmentName}` |  |
| **SKU** | `standard` |  |
| **RBAC Auth** | `true` | No access policies |
| **Purge Protection** | `true` |  |
| **Soft Delete** | 90 days |  |

**Secrets stored**:
| Secret Name | Source Parameter |
|-------------|-----------------|
| `github-client-id` | `githubClientId` |
| `github-client-secret` | `githubClientSecret` (@secure) |
| `session-secret-key` | `sessionSecretKey` (@secure) |
| `encryption-key` | `encryptionKey` (@secure) |

**Relationships**: Key Vault Secrets User role → Managed Identity.

### 6. Storage Account

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.Storage/storageAccounts` |  |
| **Name** | `st{environmentName}` | Globally unique, alphanumeric, lowercase |
| **Kind** | `StorageV2` |  |
| **SKU** | `Standard_LRS` |  |

**File Shares**:
| Share Name | Quota | Mount Target |
|------------|-------|--------------|
| `solune-data` | 1 GiB | Backend `/var/lib/solune/data` |
| `signal-config` | 1 GiB | Signal API `/home/.local/share/signal-cli` |

**Relationships**: Storage File Data SMB Share Contributor role → Managed Identity.

### 7. Azure OpenAI Account

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.CognitiveServices/accounts` |  |
| **Kind** | `OpenAI` |  |
| **Name** | `oai-{environmentName}` |  |
| **SKU** | `S0` |  |

**Model Deployment**:
| Property | Value |
|----------|-------|
| **Name** | `{openAiModelName}` (default: `gpt-4o`) |
| **Model** | `gpt-4o` |
| **Version** | `2024-08-06` |
| **Capacity** | `{deployCapacity}` (default: 10) |

**Relationships**: Cognitive Services OpenAI User role → Managed Identity. Connected to AI Foundry Hub.

### 8. AI Foundry Hub

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.MachineLearningServices/workspaces` |  |
| **Kind** | `Hub` |  |
| **Name** | `aih-{environmentName}` |  |
| **Identity** | System-assigned |  |

**Connections**: OpenAI Account, Key Vault, Storage, Log Analytics.

### 9. AI Foundry Project

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.MachineLearningServices/workspaces` |  |
| **Kind** | `Project` |  |
| **Name** | `aip-{environmentName}` |  |
| **Hub** | → AI Foundry Hub |  |

**Relationships**: Azure AI Developer role → Managed Identity.

### 10. Container Apps Environment

| Property | Value | Notes |
|----------|-------|-------|
| **Resource Type** | `Microsoft.App/managedEnvironments` |  |
| **Name** | `cae-{environmentName}` |  |
| **Log Analytics** | → Log Analytics Workspace |  |
| **Workload Profile** | `Consumption` |  |

**Storage Mounts**:
| Mount Name | Share | Access |
|------------|-------|--------|
| `solune-data` | solune-data | ReadWrite |
| `signal-config` | signal-config | ReadWrite |

### 11. Container App: Backend

| Property | Value |
|----------|-------|
| **Name** | `ca-backend-{environmentName}` |
| **Image** | `{acr}.azurecr.io/solune-backend:latest` |
| **Port** | 8000 |
| **Ingress** | Internal |
| **CPU** | 1.0 |
| **Memory** | 2Gi |
| **Min Replicas** | 1 |
| **Max Replicas** | 3 |
| **Identity** | User-assigned managed identity |
| **Health Probe** | `/api/v1/health` (liveness + readiness) |
| **Volumes** | solune-data → `/var/lib/solune/data` |

**Environment Variables**:
| Variable | Source |
|----------|--------|
| `GITHUB_CLIENT_ID` | Key Vault ref: `github-client-id` |
| `GITHUB_CLIENT_SECRET` | Key Vault ref: `github-client-secret` |
| `SESSION_SECRET_KEY` | Key Vault ref: `session-secret-key` |
| `ENCRYPTION_KEY` | Key Vault ref: `encryption-key` |
| `AI_PROVIDER` | `azure_openai` (literal) |
| `AZURE_OPENAI_ENDPOINT` | OpenAI account endpoint (output) |
| `AZURE_OPENAI_DEPLOYMENT` | `{openAiModelName}` parameter |
| `SIGNAL_API_URL` | Signal API internal FQDN |
| `FRONTEND_URL` | Frontend external FQDN |
| `CORS_ORIGINS` | Frontend external FQDN |
| `COOKIE_SECURE` | `true` |
| `DATABASE_PATH` | `/var/lib/solune/data/settings.db` |
| `HOST` | `0.0.0.0` |
| `PORT` | `8000` |
| `DEBUG` | `false` |
| `ADMIN_GITHUB_USER_ID` | `{adminGitHubUserId}` parameter |

### 12. Container App: Frontend

| Property | Value |
|----------|-------|
| **Name** | `ca-frontend-{environmentName}` |
| **Image** | `{acr}.azurecr.io/solune-frontend:latest` |
| **Port** | 8080 |
| **Ingress** | External |
| **CPU** | 0.5 |
| **Memory** | 1Gi |
| **Min Replicas** | 1 |
| **Max Replicas** | 2 |
| **Health Probe** | `/health` |

### 13. Container App: Signal API

| Property | Value |
|----------|-------|
| **Name** | `ca-signal-{environmentName}` |
| **Image** | `docker.io/bbernhard/signal-cli-rest-api:0.98` |
| **Port** | 8080 |
| **Ingress** | Internal |
| **CPU** | 0.5 |
| **Memory** | 1Gi |
| **Min Replicas** | 1 |
| **Max Replicas** | 1 |
| **Health Probe** | `/v1/health` |
| **Volumes** | signal-config → `/home/.local/share/signal-cli` |

**Environment Variables**:
| Variable | Value |
|----------|-------|
| `MODE` | `json-rpc` |
| `DEFAULT_SIGNAL_TEXT_MODE` | `styled` |

## Validation Rules

| Rule | Scope | Details |
|------|-------|---------|
| `environmentName` length | Parameter | 1–64 characters, alphanumeric + hyphens |
| ACR name uniqueness | Container Registry | Globally unique, 5–50 alphanumeric chars |
| Key Vault name uniqueness | Key Vault | Globally unique, 3–24 alphanumeric + hyphens |
| Storage name uniqueness | Storage Account | Globally unique, 3–24 lowercase alphanumeric |
| @secure parameters | Bicep | `githubClientSecret`, `sessionSecretKey`, `encryptionKey` marked `@secure()` |
| No secrets in env vars | Container Apps | All sensitive values via Key Vault references only |

## State Transitions (Deployment Lifecycle)

```text
[Not Deployed] → azd provision / Deploy Button → [Provisioning]
[Provisioning] → ARM deployment completes → [Resources Created]
[Resources Created] → azd deploy / ACR push → [Images Building]
[Images Building] → Container Apps pull images → [Running]
[Running] → Health probes pass → [Healthy]
[Healthy] → User visits frontend FQDN → [Operational]
```

## Dependency Order (Bicep Module Deployment)

```text
1. Managed Identity (no dependencies)
2. Log Analytics Workspace (no dependencies)
3. Application Insights (depends on: Log Analytics)
4. Storage Account + File Shares (depends on: Managed Identity for RBAC)
5. Container Registry (depends on: Managed Identity for RBAC)
6. Key Vault + Secrets (depends on: Managed Identity for RBAC)
7. Azure OpenAI + Model (depends on: Managed Identity for RBAC)
8. AI Foundry Hub + Project (depends on: OpenAI, Key Vault, Storage, Log Analytics, Managed Identity)
9. Container Apps Environment (depends on: Log Analytics, Storage)
10. Container Apps (depends on: Environment, ACR, Key Vault, OpenAI, Storage, Managed Identity)
```
