# Solune

[![CI](https://github.com/Boykai/solune/actions/workflows/ci.yml/badge.svg)](https://github.com/Boykai/solune/actions/workflows/ci.yml)
[![Mutation Testing](https://github.com/Boykai/solune/actions/workflows/mutation-testing.yml/badge.svg)](https://github.com/Boykai/solune/actions/workflows/mutation-testing.yml)
[![Flaky Detection](https://github.com/Boykai/solune/actions/workflows/flaky-detection.yml/badge.svg)](https://github.com/Boykai/solune/actions/workflows/flaky-detection.yml)
[![GitHub Copilot](https://img.shields.io/badge/copilot-powered-000?logo=githubcopilot&logoColor=white)](https://github.com/features/copilot)
[![License: MIT](https://img.shields.io/github/license/Boykai/solune?color=0f766e)](https://github.com/Boykai/solune/blob/main/LICENSE)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Boykai/solune?quickstart=1)
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FBoykai%2Fsolune%2Fmain%2Finfra%2Fazuredeploy.json)

> Build software with AI agents — from idea to pull request.

Solune is an agent-driven development platform that turns a feature description into working code. Design customizable Agent Pipelines through a visual GUI, assign AI agents to execute tasks in series or parallel, and track everything on your GitHub Project board — from first commit to Copilot-reviewed pull request.

## Why Solune?

Managing software projects still means juggling disconnected tools: a project board here, an AI assistant there, manual branch management everywhere. When you want AI to do real work — not just answer questions — you end up copy-pasting between chat windows, writing glue scripts, and babysitting every step.

Solune brings it all together. You describe what you want to build, design a pipeline of AI agents in a drag-and-drop interface, and launch. Each agent creates its own sub-issue, branches from the main PR, executes its task, and merges back automatically. The entire flow is tracked on your GitHub Project board with real-time status updates.

What makes Solune different is the pipeline engine. Agents run in configurable stages — series for dependent work, parallel for independent tasks. Pipelines are reusable templates. Four built-in presets ship out of the box — **GitHub** (single Copilot agent), **Spec Kit** (specify → plan → tasks → analyze → implement), **Default** (Spec Kit + QA, test, lint, review, and judge), and **App Builder** (Default + architecture) — and you can create your own pipelines with any combination of custom agents.

## Features

### AI-Powered Development

- Build apps from conversation — describe what you want, Solune scaffolds the project and creates GitHub Issues
- Customizable Agent Pipelines with series and parallel execution groups
- Live preview with start/stop controls for running applications

### Project Management

- Real-time Kanban board with drag-and-drop columns
- Context switching between applications via `/<app-name>` slash commands
- Full GitHub Projects integration — issues move across columns as agents complete work

### Communication

- Voice input with real-time transcription for chat messages
- Signal messaging — receive pipeline notifications and reply from your phone

### Safety & Guardrails

- Self-editing protection — `@admin`/`@adminlock` guards prevent agents from modifying platform core
- OAuth 2.0 authentication with CSRF protection and encrypted sessions
- Non-root containers, rate limiting, and Content Security Policy headers

## How It Works

Solune orchestrates AI agents through a customizable pipeline. You describe a feature, the platform assigns agents to execution stages, and each agent delivers working code — all tracked on your GitHub Project board.

```text
┌──────────────────── AGENT PIPELINE ────────────────────┐
│                                                        │
│  Describe      ── You describe a feature in chat       │
│       │                                                │
│       ▼                                                │
│  Stage 1       ── Agent A  ──▶ specification           │
│       │                                                │
│       ▼                                                │
│  Stage 2       ─┬ Agent B  ──▶ implementation          │
│                 └ Agent C  ──▶ tests (parallel)        │
│       │                                                │
│       ▼                                                │
│  Review        ── Copilot code review ──▶ ready to     │
│                                          merge         │
└────────────────────────────────────────────────────────┘
```

## Quick Start

### Docker (Recommended)

```bash
git clone <repository-url>
cd <repository-name>
cp solune/.env.example solune/.env
# Edit solune/.env — set GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, SESSION_SECRET_KEY
docker compose up --build -d
```

> **Need OAuth credentials?** Create a GitHub OAuth App by following the official guide:
> [Creating an OAuth app](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app).
> Set the **Homepage URL** to `http://localhost:5173` and the **Authorization callback URL** to `http://localhost:8000/api/v1/auth/github/callback`.

Open **<http://localhost:5173>**.

### GitHub Codespaces

Click **Code → Codespaces → Create codespace on main**. The dev container auto-installs everything. Copy `solune/.env.example` to `solune/.env`, add your OAuth credentials, and start the services.

See the [Setup Guide](solune/docs/setup.md) for full instructions including local development without Docker.

## Azure Deployment

Deploy the full Solune stack to Azure with a single click — backend, frontend, and Signal sidecar on Azure Container Apps with Azure OpenAI, Key Vault, and managed identity.

### Prerequisites

- An Azure subscription with Contributor + User Access Administrator permissions
- A [GitHub OAuth App](https://github.com/settings/developers) (Homepage URL and Callback URL updated post-deployment)

### One-Click Deploy

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FBoykai%2Fsolune%2Fmain%2Finfra%2Fazuredeploy.json)

Fill in the deployment form with your GitHub OAuth credentials, secret keys, and admin user ID. Deployment takes ~10 minutes.

### azd CLI Alternative

```bash
git clone https://github.com/Boykai/solune.git && cd solune
az login && azd auth login
azd init -e solune-prod
azd env set GITHUB_CLIENT_ID <your-client-id>
azd env set GITHUB_CLIENT_SECRET <your-client-secret>
azd env set SESSION_SECRET_KEY $(openssl rand -hex 32)
azd env set ENCRYPTION_KEY $(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
azd env set ADMIN_GITHUB_USER_ID <your-github-user-id>
azd up
```

### Post-Deployment

After deployment, update your GitHub OAuth App callback URL to:
`https://<frontend-fqdn>/api/v1/auth/github/callback`

## Built With

| Component | Technology |
|-----------|------------|
| **Frontend** | React 19, TypeScript 5.9, Vite 8, TanStack Query v5, Tailwind CSS 4 |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, aiosqlite (SQLite WAL), githubkit |
| **Signal** | signal-cli-rest-api (Docker sidecar) |
| **AI** | GitHub Copilot SDK (default) or Azure OpenAI (optional) |
| **Infrastructure** | Docker Compose, nginx reverse proxy, SQLite with auto-migrations |

## Documentation

Explore the full product documentation and guides:

- **[Solune Platform Overview](solune/README.md)** — The complete product deep dive: user journey, architecture, agent pipelines, and documentation index
- **[Guides & References](solune/docs/)** — Setup, configuration, API reference, testing, troubleshooting, and more

## License

[MIT](LICENSE)
