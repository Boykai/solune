# Implementation Plan: Solune Azure Deployment with Bicep IaC

**Branch**: `001-azure-deployment-bicep` | **Date**: 2026-04-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-azure-deployment-bicep/spec.md`

## Summary

Deploy the full Solune stack (FastAPI backend, React/nginx frontend, Signal sidecar) to Azure using modular Bicep IaC with a one-click "Deploy to Azure" button. The infrastructure uses Azure Container Apps, Azure OpenAI (gpt-4o), Azure AI Foundry, Azure Key Vault (managed identity, zero hardcoded secrets), Azure Container Registry, Azure Storage (Azure Files for SQLite + Signal config), and Log Analytics + Application Insights for observability. An azd template (`azure.yaml`) provides an alternative CLI-based deployment path via `azd up`.

## Technical Context

**Language/Version**: Bicep (Azure Bicep CLI latest) + ARM JSON (compiled output)
**Primary Dependencies**: Azure Container Apps, Azure OpenAI, Azure AI Foundry, Azure Key Vault, Azure Container Registry, Azure Storage, Log Analytics, Application Insights
**Storage**: SQLite on Azure Files (solune-data share); Signal config on Azure Files (signal-config share)
**Testing**: `az bicep lint`, `az deployment sub what-if`, `azd provision --preview`
**Target Platform**: Azure (Container Apps managed environment)
**Project Type**: Infrastructure-as-Code (IaC) — no application code changes
**Performance Goals**: N/A (infrastructure provisioning; runtime performance governed by Container Apps scaling rules: backend 1–3 replicas @ 1 CPU/2Gi, frontend 1–2 replicas @ 0.5 CPU/1Gi)
**Constraints**: No hardcoded secrets in container env vars; all secrets via Key Vault refs + managed identity; ARM JSON required for portal deploy button
**Scale/Scope**: 3 Container Apps, 8 Bicep modules, ~15 Azure resources total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Specification-First | ✅ PASS | spec.md created with prioritized user stories (P1–P3), acceptance criteria, and Given-When-Then scenarios |
| II. Template-Driven Workflow | ✅ PASS | All artifacts follow canonical templates from `.specify/templates/` |
| III. Agent-Orchestrated Execution | ✅ PASS | speckit.plan agent generates plan.md → research.md → data-model.md → contracts/ → quickstart.md in sequence |
| IV. Test Optionality | ✅ PASS | Testing limited to Bicep lint + what-if validation; no unit tests needed for IaC-only feature |
| V. Simplicity and DRY | ✅ PASS | Modular Bicep design (one module per service); single managed identity; existing docker-compose patterns reused in Container Apps config |

**Gate result: ALL PASS — proceeding to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/001-azure-deployment-bicep/
├── plan.md              # This file
├── research.md          # Phase 0: Technology research & decisions
├── data-model.md        # Phase 1: Bicep resource graph & entity model
├── quickstart.md        # Phase 1: Deployment quick-start guide
├── contracts/           # Phase 1: Bicep parameter contracts & API surface
│   ├── bicep-parameters.yaml
│   └── resource-outputs.yaml
└── tasks.md             # Phase 2 output (NOT created by speckit.plan)
```

### Source Code (repository root)

```text
# New files (IaC + deployment)
azure.yaml                          # azd service manifest (3 services)
infra/
├── main.bicep                      # Orchestrator — wires all modules
├── main.bicepparam                 # Parameters (env, location, secrets)
├── azuredeploy.json                # Compiled ARM for deploy button
└── modules/
    ├── monitoring.bicep            # Log Analytics + Application Insights
    ├── registry.bicep              # ACR + AcrPull role
    ├── keyvault.bicep              # Key Vault + secrets + RBAC
    ├── openai.bicep                # Azure OpenAI + gpt-4o deployment
    ├── ai-foundry.bicep            # AI Foundry hub + project
    ├── container-apps.bicep        # Container Apps Environment + 3 apps
    └── storage.bicep               # Storage Account + Azure Files shares

# Optional CI/CD
.github/workflows/deploy-azure.yml  # GitHub Actions with OIDC

# Modified files
README.md                            # Deploy button + Azure section

# Existing (unchanged)
solune/backend/Dockerfile            # Backend image (port 8000)
solune/frontend/Dockerfile           # Frontend image (port 8080)
docker-compose.yml                   # Local development (unchanged)
```

**Structure Decision**: Infrastructure-as-Code project using `infra/` directory at repository root with modular Bicep files. This follows Azure azd conventions (azure.yaml + infra/). No application source code changes — all 3 existing Dockerfiles are reused as-is. The `infra/modules/` pattern is standard for Bicep modular design.

## Constitution Check — Post-Design Re-Evaluation

*Re-evaluated after Phase 1 design artifacts complete.*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Specification-First | ✅ PASS | spec.md complete with P1–P3 user stories, acceptance criteria, and scope boundaries |
| II. Template-Driven Workflow | ✅ PASS | All 6 artifacts generated per canonical template: spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md |
| III. Agent-Orchestrated Execution | ✅ PASS | speckit.plan produced all Phase 0 + Phase 1 outputs; Phase 2 (tasks.md) deferred to speckit.tasks |
| IV. Test Optionality | ✅ PASS | No unit tests required — IaC-only feature; validation via `az bicep lint` and `az deployment what-if` |
| V. Simplicity and DRY | ✅ PASS | 8 focused Bicep modules, 1 managed identity, managed VNet, existing Dockerfiles reused. No premature abstractions. |

**Gate result: ALL PASS — ready for Phase 2 (speckit.tasks).**

## Complexity Tracking

> No constitution violations detected. All design choices favor simplicity:
> - Single managed identity (vs. per-service identities)
> - Managed VNet (vs. custom VNet with NSGs)
> - SQLite on Azure Files (vs. database migration to Azure SQL)
> - Existing Dockerfiles reused (no application code changes)
