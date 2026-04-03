# Tasks: Solune Azure Deployment with Bicep IaC

**Input**: Design documents from `/specs/001-azure-deployment-bicep/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not required — IaC-only feature. Validation via `az bicep lint`, `az deployment sub what-if`, and `azd provision --preview` (see Constitution Check IV. Test Optionality in plan.md).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **IaC project**: `infra/` at repository root with `infra/modules/` for Bicep modules
- **azd manifest**: `azure.yaml` at repository root
- **CI/CD**: `.github/workflows/` for GitHub Actions

## Phase 1: Setup (Project Scaffolding)

**Purpose**: Create the foundational project structure, azd manifest, and parameter definitions

- [x] T001 Create `infra/` and `infra/modules/` directory structure at repository root
- [x] T002 Create azd service manifest defining backend, frontend, and signal-api services in `azure.yaml`
- [x] T003 Create Bicep parameter file with environmentName, location, githubClientId, githubClientSecret (@secure), sessionSecretKey (@secure), encryptionKey (@secure), adminGitHubUserId, openAiModelName, and deployCapacity in `infra/main.bicepparam`

---

## Phase 2: Foundational (Core Bicep Modules)

**Purpose**: Independent Bicep modules that MUST exist before the orchestrator or Container Apps can be wired. Each module is a self-contained file with explicit parameters and outputs.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create user-assigned managed identity resource in `infra/modules/identity.bicep` with parameters (environmentName, location, tags) and output (identityId, identityPrincipalId, identityClientId)
- [x] T005 [P] Create Log Analytics Workspace + Application Insights in `infra/modules/monitoring.bicep` with parameters (environmentName, location, tags) and outputs (workspaceId, workspaceCustomerId, workspaceSharedKey, appInsightsConnectionString)
- [x] T006 [P] Create Azure Container Registry (Basic SKU, admin disabled) + AcrPull role assignment for managed identity in `infra/modules/registry.bicep` with parameters (environmentName, location, tags, identityPrincipalId) and outputs (registryName, registryLoginServer)
- [x] T007 [P] Create Azure Key Vault (RBAC auth, purge protection, 90-day soft-delete) + secrets (github-client-id, github-client-secret, session-secret-key, encryption-key) + Key Vault Secrets User role in `infra/modules/keyvault.bicep` with parameters (environmentName, location, tags, identityPrincipalId, githubClientId, githubClientSecret, sessionSecretKey, encryptionKey) and outputs (vaultName, vaultUri)
- [x] T008 [P] Create Azure OpenAI account (S0 SKU) + gpt-4o model deployment + Cognitive Services OpenAI User role in `infra/modules/openai.bicep` with parameters (environmentName, location, tags, identityPrincipalId, openAiModelName, deployCapacity) and outputs (openAiEndpoint, openAiDeploymentName)
- [x] T009 [P] Create AI Foundry Hub + Project (linked to OpenAI, Key Vault, Storage, Log Analytics) + Azure AI Developer role in `infra/modules/ai-foundry.bicep` with parameters (environmentName, location, tags, identityPrincipalId, openAiAccountId, keyVaultId, storageAccountId, workspaceId) and outputs (hubName, projectName)
- [x] T010 [P] Create Storage Account (StorageV2, Standard_LRS) + Azure Files shares (solune-data 1GiB, signal-config 1GiB) + Storage File Data SMB Share Contributor role in `infra/modules/storage.bicep` with parameters (environmentName, location, tags, identityPrincipalId) and outputs (storageAccountName, storageAccountId)
- [x] T011 [P] Create Container Apps Environment + 3 container apps (backend, frontend, signal-api) with ingress, scaling, health probes, Key Vault refs, Azure Files volumes, and managed identity in `infra/modules/container-apps.bicep` with parameters (environmentName, location, tags, identityId, identityClientId, registryLoginServer, workspaceCustomerId, workspaceSharedKey, vaultName, openAiEndpoint, openAiDeploymentName, storageAccountName, storageAccountKey, adminGitHubUserId) and outputs (frontendFqdn, backendFqdn, signalApiFqdn)

**Checkpoint**: All Bicep modules exist as independent, lintable files with defined interfaces

---

## Phase 3: User Story 1 — One-Click Azure Deployment (Priority: P1) 🎯 MVP

**Goal**: A user clicks "Deploy to Azure" in the README, fills in a form, and gets a fully running Solune instance on Azure — backend, frontend, and Signal sidecar all operational.

**Independent Test**: Click the deploy button in README → complete Azure Portal form with test parameters → verify frontend loads at generated FQDN → authenticate with GitHub OAuth.

### Implementation for User Story 1

- [x] T012 [US1] Create main Bicep orchestrator that wires all modules together — managed identity, monitoring, registry, key vault, openai, ai-foundry, storage, container-apps — passes outputs between modules and tags all resources with azd-env-name in `infra/main.bicep`
- [x] T013 [US1] Compile `infra/main.bicep` to ARM JSON template via `az bicep build` and save to `infra/azuredeploy.json`
- [x] T014 [US1] Add "Deploy to Azure" button badge at top of Quick Start section and new "Azure Deployment" section with prerequisites, one-click button (URL-encoded link to azuredeploy.json), azd up alternative, and post-deployment OAuth redirect URI configuration in `README.md`

**Checkpoint**: At this point, User Story 1 should be fully functional — deploy button in README → Azure Portal form → all resources provisioned → frontend accessible

---

## Phase 4: User Story 2 — Secure Secret Management (Priority: P1)

**Goal**: All sensitive configuration (GitHub Client Secret, session secret key, encryption key) is stored in Azure Key Vault and accessed by the backend via managed identity — no secrets in container environment variables or source code.

**Independent Test**: After deployment, inspect backend container app environment variables to confirm only Key Vault references (no plaintext secrets). Verify backend starts and reads secrets from Key Vault via managed identity.

### Implementation for User Story 2

- [x] T015 [US2] Verify and refine Key Vault secret references in backend container app configuration — ensure env vars (GITHUB_CLIENT_SECRET, SESSION_SECRET_KEY, ENCRYPTION_KEY) use `secretRef` pointing to Key Vault secrets, not literal values, in `infra/modules/container-apps.bicep`
- [x] T016 [US2] Verify managed identity role assignment for Key Vault Secrets User is correctly scoped and that the identity is assigned to the backend container app in `infra/modules/keyvault.bicep` and `infra/modules/container-apps.bicep`

**Checkpoint**: At this point, no secrets are exposed in container env vars — only Key Vault refs + managed identity

---

## Phase 5: User Story 3 — Azure OpenAI-Powered AI Features (Priority: P1)

**Goal**: The backend uses Azure OpenAI (gpt-4o) via managed identity for AI content generation — no API keys, using the `azure_openai` provider configuration.

**Independent Test**: Deploy the instance, log in, navigate to a board, trigger AI generation → verify content is generated. Check backend logs to confirm requests go to Azure OpenAI endpoint.

### Implementation for User Story 3

- [x] T017 [US3] Verify and refine Azure OpenAI environment variable wiring in backend container app — ensure AI_PROVIDER=azure_openai, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT are set from OpenAI module outputs in `infra/modules/container-apps.bicep`
- [x] T018 [US3] Verify Cognitive Services OpenAI User role assignment is correctly scoped to the OpenAI account for the managed identity in `infra/modules/openai.bicep`

**Checkpoint**: AI generation works end-to-end via Azure OpenAI with managed identity authentication

---

## Phase 6: User Story 4 — Modular Infrastructure as Code (Priority: P2)

**Goal**: Bicep code is organized into self-contained modules with clear inputs/outputs. Each module can be reviewed, modified, or replaced independently. All code passes linting.

**Independent Test**: Run `az bicep lint --file infra/main.bicep` → zero errors. Run `az deployment sub what-if` → expected resources shown. Each module file has documented parameters and outputs.

### Implementation for User Story 4

- [x] T019 [US4] Add descriptive comments and @description decorators to all parameters and outputs across all Bicep module files in `infra/modules/*.bicep`
- [x] T020 [US4] Run `az bicep lint --file infra/main.bicep` and fix any linting errors across all Bicep files in `infra/`

**Checkpoint**: All Bicep code is modular, self-documenting, and lint-clean

---

## Phase 7: User Story 5 — azd Template for CLI Deployment (Priority: P2)

**Goal**: A developer can clone the repo, run `azd up`, and get a fully deployed Solune instance — as an alternative to the portal deploy button.

**Independent Test**: Run `azd provision --preview` → verify expected resource list matches Bicep definitions. Run `azd up` → full build-provision-deploy cycle completes.

### Implementation for User Story 5

- [x] T021 [US5] Verify and refine azd manifest to ensure all three services (backend, frontend, signal-api) correctly point to their Dockerfiles and target Container App resource names in `azure.yaml`
- [x] T022 [US5] Verify `infra/main.bicepparam` integrates correctly with azd environment variables for all required parameters in `infra/main.bicepparam`

**Checkpoint**: `azd up` produces an identical environment to the deploy button path

---

## Phase 8: User Story 6 — Automated CI/CD Pipeline (Priority: P3)

**Goal**: Every push to main triggers automated Azure provisioning and deployment via GitHub Actions with OIDC federated credentials — no static secrets in GitHub.

**Independent Test**: Verify workflow file syntax. Push a test commit to main → GitHub Actions run completes with OIDC authentication → `azd provision` + `azd deploy` succeed.

### Implementation for User Story 6

- [x] T023 [US6] Create GitHub Actions workflow with OIDC federated credentials for Azure, running `azd provision` + `azd deploy` on push to main in `.github/workflows/deploy-azure.yml`

**Checkpoint**: Automated CI/CD pipeline deploys on push to main with zero static secrets

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation polish, and cross-cutting improvements

- [x] T024 [P] Run `az bicep lint --file infra/main.bicep` final validation and fix any remaining issues across `infra/`
- [x] T025 [P] Verify frontend→backend routing: nginx proxy to backend internal FQDN, CORS_ORIGINS + FRONTEND_URL set to frontend external FQDN, COOKIE_SECURE=true in `infra/modules/container-apps.bicep`
- [x] T026 [P] Verify RBAC consolidation: single managed identity with all 5 roles (AcrPull, Key Vault Secrets User, Cognitive Services OpenAI User, Azure AI Developer, Storage File Data SMB Share Contributor) correctly wired in `infra/main.bicep`
- [x] T027 Re-compile `infra/main.bicep` to `infra/azuredeploy.json` if any Bicep changes were made in previous phases via `az bicep build`
- [x] T028 Run `specs/001-azure-deployment-bicep/quickstart.md` validation — verify all commands and URLs are accurate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (directory structure exists) — all module tasks [P] can run in parallel
- **User Story 1 (Phase 3)**: Depends on Phase 2 (all modules must exist for main.bicep orchestrator)
- **User Story 2 (Phase 4)**: Depends on Phase 2 + Phase 3 (refines T007 + T011 outputs)
- **User Story 3 (Phase 5)**: Depends on Phase 2 + Phase 3 (refines T008 + T011 outputs)
- **User Story 4 (Phase 6)**: Depends on Phase 3 (all Bicep files must exist to lint/document)
- **User Story 5 (Phase 7)**: Depends on Phase 1 + Phase 3 (azure.yaml + main.bicep must exist)
- **User Story 6 (Phase 8)**: Can start after Phase 1 — independent CI/CD file
- **Polish (Phase 9)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)**: Requires Phase 2 complete → delivers deploy button + full infrastructure
- **US2 (P1)**: Requires US1 → refines/validates Key Vault secret management
- **US3 (P1)**: Requires US1 → refines/validates OpenAI integration
- **US4 (P2)**: Requires US1 → linting and documentation of existing modules
- **US5 (P2)**: Requires US1 → validates azd integration
- **US6 (P3)**: Independent — can be developed in parallel with US4/US5

### Within Each User Story

- Modules (Phase 2) before orchestrator (US1)
- Orchestrator before ARM compilation (US1)
- ARM compilation before deploy button (US1)
- Core implementation before refinement stories (US2, US3)

### Parallel Opportunities

- **Phase 2 (all 8 module tasks T004–T011)**: All modules are independent files — full parallelism
- **Phase 8 (US6)**: CI/CD workflow is independent — can run in parallel with US4/US5
- **Phase 9 (T024–T026)**: All polish tasks marked [P] can run in parallel

---

## Parallel Example: Phase 2 (Foundational Modules)

```bash
# All 8 Bicep modules can be created simultaneously (different files, no dependencies):
Task: "Create managed identity in infra/modules/identity.bicep"           # T004
Task: "Create monitoring in infra/modules/monitoring.bicep"               # T005
Task: "Create registry in infra/modules/registry.bicep"                   # T006
Task: "Create key vault in infra/modules/keyvault.bicep"                  # T007
Task: "Create openai in infra/modules/openai.bicep"                       # T008
Task: "Create ai-foundry in infra/modules/ai-foundry.bicep"               # T009
Task: "Create storage in infra/modules/storage.bicep"                     # T010
Task: "Create container-apps in infra/modules/container-apps.bicep"       # T011
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational modules (T004–T011) — **all in parallel**
3. Complete Phase 3: User Story 1 (T012–T014) — orchestrator + ARM + README
4. **STOP and VALIDATE**: `az bicep lint`, deploy button works, frontend loads
5. Deploy/demo if ready — this is a fully working Azure deployment

### Incremental Delivery

1. Setup + Foundational → All modules exist
2. Add US1 (T012–T014) → Deploy button works → **MVP delivered!**
3. Add US2 (T015–T016) → Validate secret management hardening
4. Add US3 (T017–T018) → Validate AI integration refinement
5. Add US4 (T019–T020) → Documentation + lint validation
6. Add US5 (T021–T022) → azd CLI path validated
7. Add US6 (T023) → CI/CD automated (optional)
8. Polish (T024–T028) → Final cross-cutting validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (Phase 1) together
2. **Developer A–H**: Each takes one Bicep module (Phase 2) — full parallelism
3. Once Phase 2 is done:
   - **Developer A**: US1 (orchestrator + deploy button)
   - **Developer B**: US6 (CI/CD — independent)
4. After US1 merges:
   - **Developer A**: US2 + US3 (refinement stories)
   - **Developer C**: US4 (linting + documentation)
   - **Developer D**: US5 (azd validation)
5. Everyone: Polish (Phase 9)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- No unit tests required — IaC-only feature validated via Bicep lint + what-if
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- ARM JSON (`azuredeploy.json`) must be re-compiled whenever Bicep files change
- All secrets flow through Key Vault — never as literal container env vars
