# Feature Specification: Solune Azure Deployment with Bicep IaC

**Feature Branch**: `001-azure-deployment-bicep`  
**Created**: 2026-04-03  
**Status**: Draft  
**Input**: User description: "Deploy Solune (FastAPI backend + React/nginx frontend + Signal sidecar) to Azure using Bicep IaC with a single-click Deploy to Azure button. Uses Azure Container Apps, Azure OpenAI, Azure AI Foundry, Azure Key Vault, managed identity, and an azd template — no hardcoded secrets."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-Click Azure Deployment (Priority: P1)

A developer or team lead discovers Solune and wants to deploy the full stack (backend, frontend, Signal sidecar) to Azure. They click a "Deploy to Azure" button in the project README, fill in a short form of required parameters (GitHub OAuth credentials, admin user ID, preferred Azure region), and Azure provisions all infrastructure automatically. After deployment completes, the frontend is accessible via a public URL and the user can log in with GitHub OAuth.

**Why this priority**: This is the primary entry point for Azure adoption. Without a working one-click deployment, no other Azure features can be used. It delivers the core value proposition of zero-manual-setup cloud deployment.

**Independent Test**: Can be fully tested by clicking the deploy button in the README, completing the Azure Portal form with test parameters, and verifying the frontend loads at the generated FQDN. Delivers a fully running Solune instance on Azure.

**Acceptance Scenarios**:

1. **Given** the project README contains a "Deploy to Azure" button, **When** a user clicks the button, **Then** the Azure Portal opens with a pre-filled custom deployment form showing all required parameters.
2. **Given** the user fills in required parameters (GitHub Client ID, GitHub Client Secret, admin GitHub User ID, session secret key, encryption key) and clicks "Create", **When** the deployment runs, **Then** all Azure resources (Container Apps, Key Vault, OpenAI, Storage, Registry, Monitoring) are provisioned within 15 minutes.
3. **Given** deployment has completed successfully, **When** the user navigates to the frontend FQDN shown in the deployment outputs, **Then** the Solune login page loads and the user can authenticate via GitHub OAuth.
4. **Given** deployment has completed, **When** the user navigates to a board and triggers AI generation, **Then** content is generated successfully using Azure OpenAI.

---

### User Story 2 - Secure Secret Management (Priority: P1)

A platform operator deploying Solune to Azure needs assurance that no secrets (API keys, OAuth credentials, encryption keys) are exposed in container environment variables or source code. All sensitive configuration is stored in Azure Key Vault and accessed via managed identity — no static credentials anywhere in the running system.

**Why this priority**: Security is a non-negotiable requirement for production deployment. Exposed secrets in environment variables or logs represent a critical vulnerability. This must be in place before any production use.

**Independent Test**: Can be tested by inspecting the deployed container app configuration to confirm no secret values appear in environment variables — only Key Vault references — and verifying the backend can successfully read secrets via managed identity.

**Acceptance Scenarios**:

1. **Given** the deployment has completed, **When** an operator inspects the backend container app's environment variables, **Then** no plaintext secrets are present — only Key Vault secret references.
2. **Given** the backend container starts, **When** it initializes and reads configuration, **Then** it retrieves secrets (GitHub Client Secret, session secret key, encryption key) from Key Vault using the assigned managed identity.
3. **Given** the managed identity has Key Vault Secrets User role, **When** the backend requests secrets, **Then** access succeeds without any static credentials or connection strings.

---

### User Story 3 - Azure OpenAI-Powered AI Features (Priority: P1)

A Solune user on the Azure deployment accesses AI generation features (e.g., generating board content). The system uses Azure OpenAI with a dedicated gpt-4o model deployment. The backend authenticates to Azure OpenAI using an `AZURE_OPENAI_KEY` secret that is provisioned and stored in Azure Key Vault as part of the deployment. This provides reliable, production-grade AI without requiring individual user OAuth tokens.

**Why this priority**: AI generation is a core Solune feature. Using Azure OpenAI (instead of Copilot SDK) ensures reliable production access without per-user token management, making it critical for the Azure deployment path.

**Independent Test**: Can be tested by logging into the deployed Solune instance, navigating to a board, and triggering AI content generation. Backend logs confirm requests route to Azure OpenAI and succeed using the configured API key.

**Acceptance Scenarios**:

1. **Given** the backend is configured with AI_PROVIDER=azure_openai, **When** a user triggers AI content generation from the Solune UI, **Then** the request is sent to the Azure OpenAI endpoint (not Copilot SDK).
2. **Given** the Azure OpenAI account has a gpt-4o model deployment and the `AZURE_OPENAI_KEY` secret is provisioned in Key Vault, **When** the backend sends a generation request, **Then** it authenticates using the configured Azure OpenAI API key and receives a successful response.
3. **Given** the Azure OpenAI service is temporarily unavailable, **When** a user triggers AI generation, **Then** the system displays a user-friendly error message indicating the service is temporarily unavailable.
4. **Note**: Direct managed-identity authentication to Azure OpenAI is a future enhancement requiring backend code changes before the `AZURE_OPENAI_KEY` dependency can be removed.

---

### User Story 4 - Modular Infrastructure as Code (Priority: P2)

A DevOps engineer wants to understand, customize, or extend the Azure infrastructure. The Bicep code is organized into self-contained modules (one per Azure service), orchestrated by a single main file. Each module can be reviewed, modified, or replaced independently. All Bicep code passes linting without errors.

**Why this priority**: Modularity enables long-term maintainability and team adoption. While not required for initial deployment, it is essential for any production team that needs to customize or extend the infrastructure.

**Independent Test**: Can be tested by running Bicep linting on the main file and verifying each module is self-contained with clearly defined inputs and outputs. A dry-run deployment preview confirms the expected resources.

**Acceptance Scenarios**:

1. **Given** the infra/ directory contains Bicep modules, **When** a DevOps engineer runs linting on the main orchestrator file, **Then** there are zero lint errors across all modules.
2. **Given** each Bicep module has defined parameters and outputs, **When** an engineer reviews a single module (e.g., keyvault.bicep), **Then** they can understand its purpose, inputs, and outputs without reading other modules.
3. **Given** the main Bicep file orchestrates all modules, **When** a dry-run deployment is performed, **Then** it shows all expected Azure resources would be created with correct dependencies.

---

### User Story 5 - azd Template for CLI Deployment (Priority: P2)

A developer prefers command-line workflows over the Azure Portal. They clone the Solune repository, run `azd up`, and the tool builds all three service containers, provisions infrastructure, and deploys everything — as an alternative to the one-click button.

**Why this priority**: Provides a developer-friendly CLI alternative for those who prefer terminal workflows or need to integrate deployment into scripts. Complements the one-click button for different user personas.

**Independent Test**: Can be tested by running `azd provision --preview` to verify the expected resource list, then `azd up` to perform a full build-provision-deploy cycle.

**Acceptance Scenarios**:

1. **Given** azure.yaml exists at the project root defining three services (backend, frontend, signal-api), **When** a developer runs `azd up`, **Then** all three containers are built and deployed to Azure Container Apps.
2. **Given** the azd template is properly configured, **When** a developer runs `azd provision --preview`, **Then** it shows all expected Azure resources matching the Bicep definitions.

---

### User Story 6 - Automated CI/CD Pipeline (Priority: P3)

A development team wants controlled deployments triggered via GitHub Actions. The workflow uses OIDC federated credentials — no static secrets stored in GitHub. Deployments are triggered manually via `workflow_dispatch` for safety, allowing teams to control when infrastructure changes are applied.

**Why this priority**: Automation is a best practice but not required for initial deployment. Teams can manually deploy first and add CI/CD later. Manual dispatch is the safer default for IaC; a push-to-main trigger can be added once teams are confident. This is optional and can be developed in parallel.

**Independent Test**: Can be tested by verifying the workflow file syntax, then manually triggering the workflow and confirming the GitHub Actions run completes successfully with OIDC authentication.

**Acceptance Scenarios**:

1. **Given** the CI/CD workflow file exists, **When** a team member triggers the workflow manually via `workflow_dispatch`, **Then** the workflow runs `azd provision` followed by `azd deploy`.
2. **Given** OIDC federated credentials are configured in the GitHub repository, **When** the workflow authenticates with Azure, **Then** no static secrets are used — only OIDC token exchange.

---

### Edge Cases

- What happens when an Azure region does not support all required services (e.g., Azure OpenAI is not available in the selected region)? The deployment should fail fast with a clear error message indicating which service is unavailable in the chosen region.
- What happens when the user provides an invalid GitHub OAuth Client ID or Client Secret? The deployment succeeds but login fails; post-deployment documentation should guide the user to verify OAuth credentials.
- What happens when the Azure subscription has insufficient quota for Container Apps or OpenAI? The deployment should surface Azure's quota error messages clearly so the user knows what to request.
- What happens when the Key Vault name is already taken globally? The naming convention should include environment-specific suffixes to minimize collisions; if a collision occurs, the user receives a clear error to choose a different environment name.
- What happens when Azure Files storage becomes unavailable after deployment? The backend should handle storage errors gracefully, returning service-unavailable responses rather than crashing.
- What happens when the deploy button ARM template URL becomes invalid (e.g., repository is renamed or made private)? The README should document that the deploy button URL is tied to the repository path and must be updated if the repository moves.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a "Deploy to Azure" button in the project README that opens the Azure Portal with a pre-configured deployment form.
- **FR-002**: System MUST define an azd manifest (azure.yaml) at the project root specifying three services: backend, frontend, and signal-api, each pointing to its respective Dockerfile.
- **FR-003**: System MUST provision Azure Container Apps for three services: backend (port 8000, internal ingress, 1–3 replicas, 1 CPU / 2 GiB), frontend (port 8080, external ingress, 1–2 replicas, 0.5 CPU / 1 GiB), and signal-api (port 8080, internal ingress, 0.5 CPU / 1 GiB).
- **FR-004**: System MUST store all sensitive configuration (GitHub Client Secret, session secret key, encryption key) in Azure Key Vault with RBAC authorization, purge protection enabled, and 90-day soft-delete.
- **FR-005**: System MUST create a single user-assigned managed identity with the following RBAC roles: AcrPull, Key Vault Secrets User, Cognitive Services OpenAI User, Azure AI Developer, and Storage File Data SMB Share Contributor.
- **FR-006**: System MUST provision an Azure OpenAI account with a gpt-4o model deployment, accessible by the backend via managed identity.
- **FR-007**: System MUST provision an Azure AI Foundry hub and project linked to the OpenAI account, Key Vault, and Log Analytics workspace.
- **FR-008**: System MUST provision Azure Container Registry (Basic tier, admin access disabled) with the managed identity granted AcrPull role.
- **FR-009**: System MUST provision a Storage Account with two Azure Files shares (solune-data for SQLite persistence, signal-config for Signal configuration) and appropriate RBAC.
- **FR-010**: System MUST provision a Log Analytics Workspace and Application Insights instance for monitoring and diagnostics.
- **FR-011**: System MUST configure the frontend container to proxy requests to the backend using the backend's internal FQDN, with the backend's CORS_ORIGINS and FRONTEND_URL set to the frontend's external FQDN and COOKIE_SECURE=true.
- **FR-012**: System MUST organize Bicep code into separate modules: monitoring, registry, keyvault, openai, ai-foundry, container-apps, and storage, orchestrated by a single main.bicep file.
- **FR-013**: System MUST compile main.bicep to an ARM JSON template (azuredeploy.json) for the deploy button, since the Azure Portal cannot consume raw Bicep.
- **FR-014**: System MUST configure health probes for each container app: backend at /api/v1/health, frontend at /health, and signal-api at /v1/health.
- **FR-015**: System MUST accept the following deployment parameters: environmentName, location, githubClientId, githubClientSecret (secure), sessionSecretKey (secure), encryptionKey (secure), adminGitHubUserId, openAiModelName, and deployment capacity.
- **FR-016**: System MUST tag all provisioned resources with the azd environment name for identification and lifecycle management.
- **FR-017**: System MUST mount Azure Files volumes to the backend container (for SQLite database) and signal-api container (for Signal configuration).
- **FR-018**: System MUST update the README with a "Deploy to Azure" badge, an Azure Deployment section covering prerequisites, one-click deployment, azd alternative, and post-deployment configuration (OAuth redirect URI update).

### Key Entities

- **Container App**: A running service instance (backend, frontend, or signal-api) with defined CPU/memory, ingress rules, scaling, health probes, and environment configuration. Backend and signal-api use internal ingress; frontend uses external ingress.
- **Managed Identity**: A single user-assigned identity shared by all services, granting access to Key Vault, Container Registry, OpenAI, AI Foundry, and Azure Files without static credentials.
- **Key Vault**: A centralized secure store for all sensitive configuration values (GitHub OAuth secret, session key, encryption key), accessed exclusively via managed identity RBAC.
- **Bicep Module**: A self-contained infrastructure-as-code file defining one Azure service or group of related resources, with explicit parameters and outputs for composability.
- **azd Template**: The azure.yaml manifest plus Bicep files that enable `azd up` CLI deployment as an alternative to the portal deploy button.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can go from clicking "Deploy to Azure" to a fully operational Solune instance (login page visible, OAuth working) in under 20 minutes with no manual infrastructure configuration.
- **SC-002**: Zero secrets are exposed in container environment variables, deployment logs, or source code — all sensitive values are stored in and retrieved from the secure vault.
- **SC-003**: AI content generation works end-to-end on the deployed instance: a user logs in, navigates to a board, triggers generation, and receives AI-generated content within 10 seconds.
- **SC-004**: All infrastructure code passes linting with zero errors, and a dry-run deployment preview matches the expected set of resources.
- **SC-005**: The CLI deployment path (`azd up`) produces an identical running environment to the one-click button path — both result in the same set of resources and working application.
- **SC-006**: All three container services (backend, frontend, signal-api) pass their configured health checks within 2 minutes of deployment completion.
- **SC-007**: The infrastructure is fully modular: an engineer can identify, understand, and modify any single service's configuration without reading unrelated modules.
- **SC-008**: Post-deployment, the only manual step required is updating the GitHub OAuth App redirect URI to point to the new frontend FQDN.

## Assumptions

- The deploying user has an active Azure subscription with sufficient quota for Container Apps, Azure OpenAI, and related services.
- The deploying user has a registered GitHub OAuth App and can provide its Client ID and Client Secret.
- The target Azure region supports all required services (Azure OpenAI, Container Apps, AI Foundry). The deployment documentation will list recommended regions.
- The existing Solune Dockerfiles (backend, frontend, signal-api) are ready for Azure Container Registry builds without modification.
- SQLite on Azure Files provides sufficient performance for the current Solune workload. Migration to a managed database is out of scope and can be addressed in a future feature.
- The managed VNet provided by Azure Container Apps is sufficient for internal service-to-service communication (no custom VNet required).

## Scope

### In Scope

- Azure Container Apps for all 3 services (backend, frontend, signal-api)
- Azure OpenAI with gpt-4o model deployment
- Azure AI Foundry hub and project
- Azure Key Vault for secret management
- Azure Container Registry for container images
- Azure Storage (Azure Files) for SQLite persistence and Signal configuration
- Log Analytics Workspace and Application Insights for monitoring
- Single user-assigned managed identity with all required RBAC roles
- Deploy to Azure button (compiled ARM JSON template)
- azd template (azure.yaml)
- README updates with deployment documentation
- Optional CI/CD workflow for automated deployments

### Out of Scope

- Custom domain and SSL certificate management (can be added later as optional parameters)
- Migration from SQLite to Azure SQL or Cosmos DB
- Custom VNet peering or advanced networking (using Container Apps managed networking)
- Multi-region deployment or geo-replication
- Azure Front Door or CDN integration
- Automated database backup and restore procedures

## Decisions

| Decision | Rationale |
| -------- | --------- |
| AI_PROVIDER=azure_openai | More reliable for production than Copilot SDK which requires per-user OAuth tokens |
| SQLite on Azure Files | Simplest persistence that matches the existing docker-compose volume pattern |
| Signal as separate Container App | Mirrors the docker-compose sidecar pattern with internal ingress |
| Single user-assigned managed identity | Sufficient at current scale; simpler than per-service identities |
| Managed VNet (no custom VNet) | Container Apps built-in networking handles internal service communication |
| ARM JSON for deploy button | Azure Portal requires compiled ARM templates, not raw Bicep files |
