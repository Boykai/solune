# Research: Solune Azure Deployment with Bicep IaC

**Date**: 2026-04-03 | **Plan**: [plan.md](./plan.md)

## Research Tasks & Findings

### 1. Azure Container Apps — Bicep Patterns for Multi-Service Deployments

**Decision**: Use `Microsoft.App/managedEnvironments` with `Microsoft.App/containerApps` resources, one per service.

**Rationale**: Container Apps Environment provides shared networking, logging, and scaling. Each service is a separate Container App resource with its own ingress, scaling rules, and container configuration. This mirrors the docker-compose multi-service pattern.

**Alternatives Considered**:
- **Azure Kubernetes Service (AKS)**: Overkill for 3 services; requires Kubernetes expertise and more operational overhead.
- **Azure App Service**: Doesn't natively support sidecar containers or internal-only ingress between services.
- **Azure Container Instances**: No built-in scaling, load balancing, or managed ingress.

**Best Practices Applied**:
- Use `workloadProfileType: 'Consumption'` for cost-effective auto-scaling
- Set `activeRevisionsMode: 'Single'` for predictable deployments
- Use managed identity (not admin credentials) for ACR pull
- Configure liveness and readiness probes matching existing health endpoints
- Use `internal: true` ingress for backend and signal-api; `external: true` only for frontend

### 2. Azure Key Vault — Secret Management with Managed Identity

**Decision**: Use `Microsoft.KeyVault/vaults` with RBAC authorization model (not access policies). Store secrets via Bicep `Microsoft.KeyVault/vaults/secrets`. Reference secrets in Container Apps using `secretRef` with Key Vault references.

**Rationale**: RBAC authorization is the modern best practice — it uses Azure RBAC instead of vault-level access policies, providing granular control and consistent management. Container Apps support native Key Vault references, meaning the secret value is never exposed in environment variables.

**Alternatives Considered**:
- **Access policy model**: Legacy; harder to audit and manage at scale.
- **Direct env vars with @secure Bicep params**: Secrets would appear in ARM deployment history.
- **Azure App Configuration**: Overkill for secret-only storage.

**Best Practices Applied**:
- Enable purge protection and soft-delete (90 days) for production safety
- Use `Key Vault Secrets User` role (not `Key Vault Administrator`) for least-privilege
- Store: GITHUB_CLIENT_SECRET, SESSION_SECRET_KEY, ENCRYPTION_KEY, GITHUB_WEBHOOK_SECRET
- Never pass @secure parameter values to container environment directly

### 3. Azure OpenAI — Deployment with API Key Authentication

**Decision**: Use `Microsoft.CognitiveServices/accounts` (kind: `OpenAI`) with a `Microsoft.CognitiveServices/accounts/deployments` for gpt-4o model. Authenticate using the Azure OpenAI API key required by the current backend implementation, and store that key in Key Vault for injection into the backend as `AZURE_OPENAI_KEY`.

**Rationale**: The current Solune backend configuration requires `AZURE_OPENAI_KEY` at startup and the `AzureOpenAICompletionProvider` uses static API-key authentication. The deployment provisions the Azure OpenAI account and model, retrieves the service key securely via `listKeys()`, stores it in Key Vault, and references it from the backend Container App via Key Vault secret ref. Managed identity authentication (via `DefaultAzureCredential`) is a desirable future enhancement but would require backend code changes before `AZURE_OPENAI_KEY` can be removed.

**Alternatives Considered**:
- **Managed identity authentication**: Preferred long-term because it avoids API key rotation and secret distribution, but not supported by the current backend implementation without code changes.
- **GitHub Copilot SDK**: Requires per-user OAuth tokens; not suitable for server-side production use.

**Best Practices Applied**:
- Use `S0` SKU for OpenAI (standard tier)
- Set deployment capacity via parameter (default: 10 TPM units)
- Use `2024-08-06` model version or latest available
- Store the Azure OpenAI API key in Key Vault and reference it securely from the backend Container App as `AZURE_OPENAI_KEY`
- Assign `Cognitive Services OpenAI User` role to managed identity for future managed-identity auth support

### 4. Azure AI Foundry — Hub + Project Configuration

**Decision**: Use `Microsoft.MachineLearningServices/workspaces` with kind `Hub` for the AI Foundry hub, and kind `Project` for the project workspace. Link to OpenAI account, Key Vault, and Log Analytics.

**Rationale**: AI Foundry provides a unified management plane for AI resources, model experimentation, and evaluation. The hub-project pattern separates organizational resources from feature-specific work.

**Alternatives Considered**:
- **Standalone Azure OpenAI only**: Works but loses the management/experimentation capabilities of AI Foundry.
- **Azure ML Workspace (classic)**: Being deprecated in favor of AI Foundry.

**Best Practices Applied**:
- Hub links to: OpenAI account (AI Services connection), Key Vault, Storage, Log Analytics
- Project links to Hub (child workspace)
- Assign `Azure AI Developer` role to managed identity for project access
- Use `systemAssigned` identity for the hub itself; `userAssigned` for container apps

### 5. Azure Storage — Azure Files for SQLite Persistence

**Decision**: Use `Microsoft.Storage/storageAccounts` with `Microsoft.Storage/storageAccounts/fileServices/shares` for two shares: `solune-data` (SQLite DB) and `signal-config` (Signal CLI state). Mount as Azure Files volumes in Container Apps.

**Rationale**: Azure Files provides SMB/NFS file shares that can be mounted as volumes in Container Apps, directly replacing docker-compose named volumes. SQLite works on Azure Files with SMB because it supports byte-range locking.

**Alternatives Considered**:
- **Azure Blob Storage**: Not suitable for SQLite (no file locking support).
- **Azure SQL / Cosmos DB**: Requires application code changes to replace SQLite.
- **Container Apps built-in storage**: Ephemeral; data lost on restart.

**Best Practices Applied**:
- Use `StorageV2` account kind with `Standard_LRS` redundancy
- Enable `Storage File Data SMB Share Contributor` RBAC role for managed identity
- Set quota on shares (solune-data: 1Gi, signal-config: 1Gi)
- Mount as ReadWrite in Container Apps volume configuration

### 6. Azure Container Registry — Image Management

**Decision**: Use `Microsoft.ContainerRegistry/registries` with `Basic` SKU. Disable admin user. Grant `AcrPull` role to the managed identity used by Container Apps.

**Rationale**: Basic SKU is cost-effective for small deployments. Admin credentials are a security anti-pattern; managed identity with AcrPull role is the recommended approach.

**Alternatives Considered**:
- **Docker Hub / GitHub Container Registry**: External registry adds network latency and requires separate credentials.
- **Standard/Premium ACR SKU**: Unnecessary for this scale.

**Best Practices Applied**:
- `adminUserEnabled: false` — enforce managed identity only
- `AcrPull` role (not `AcrPush`) for Container Apps — least privilege
- ACR name must be globally unique — use `${environmentName}acr` pattern

### 7. Managed Identity — Consolidated RBAC Strategy

**Decision**: Single `Microsoft.ManagedIdentity/userAssignedIdentities` resource assigned to the backend Container App. One identity holds all required roles.

**Rationale**: At this scale (3 services, 1 backend needing secrets/AI access), a single identity is simpler to manage than per-service identities. The frontend and signal-api only need ACR pull (via the Container Apps Environment level).

**Roles assigned to managed identity**:
| Role | Resource Scope | Purpose |
|------|---------------|---------|
| AcrPull | Container Registry | Pull container images |
| Key Vault Secrets User | Key Vault | Read secrets |
| Cognitive Services OpenAI User | OpenAI Account | Call AI models |
| Azure AI Developer | AI Foundry Project | Access AI Foundry |
| Storage File Data SMB Share Contributor | Storage Account | Mount Azure Files |

**Alternatives Considered**:
- **System-assigned identity per Container App**: More identities to manage; complicates RBAC.
- **Service principal with client secret**: Requires secret rotation; less secure.

### 8. ARM JSON Compilation for Deploy Button

**Decision**: Compile `infra/main.bicep` to `infra/azuredeploy.json` using `az bicep build`. The deploy button URL points to this compiled ARM template.

**Rationale**: The Azure Portal "Deploy to Azure" button only accepts ARM JSON templates, not Bicep. The compiled JSON must be committed to the repository so the button URL can reference it via raw GitHub URL.

**Best Practices Applied**:
- Button URL format: `https://portal.azure.com/#create/Microsoft.Template/uri/{encoded-raw-url}`
- Raw URL: `https://raw.githubusercontent.com/Boykai/solune/main/infra/azuredeploy.json`
- Re-compile and commit `azuredeploy.json` whenever `main.bicep` or modules change
- Badge markdown: `[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](url)`

### 9. Frontend → Backend Routing in Container Apps

**Decision**: The nginx frontend proxies `/api/` requests to the backend's internal FQDN (e.g., `http://backend.internal.{env}.{region}.azurecontainerapps.io`). The backend's `CORS_ORIGINS` and `FRONTEND_URL` are set to the frontend's external FQDN.

**Rationale**: This mirrors the existing docker-compose networking where nginx proxies to `http://backend:8000`. In Container Apps, internal ingress provides a DNS-resolvable FQDN within the managed environment.

**Key Configuration**:
- Frontend nginx.conf already proxies `/api/` to `http://backend:8000` — for Azure, override via build arg or runtime env to use the backend's internal FQDN
- Backend env: `CORS_ORIGINS=https://{frontend-fqdn}`, `FRONTEND_URL=https://{frontend-fqdn}`
- Backend env: `COOKIE_SECURE=true` (HTTPS in production)
- The frontend Dockerfile accepts `VITE_API_BASE_URL` build arg (default `/api/v1`)

### 10. Container Apps Environment — Networking

**Decision**: Use managed VNet (default Container Apps networking) with workload profiles. No custom VNet.

**Rationale**: Managed VNet provides internal service discovery, automatic DNS for internal-ingress apps, and TLS termination at the environment level. Custom VNet adds complexity without benefit at this scale.

**Service Communication**:
- Frontend (external) → Backend (internal): via nginx proxy using backend's internal FQDN
- Backend → Signal API (internal): via `SIGNAL_API_URL=http://signal-api.internal.{env}.{region}.azurecontainerapps.io:8080`
- Backend → Azure OpenAI: via public endpoint with managed identity
- Backend → Key Vault: via public endpoint with managed identity
