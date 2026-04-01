# Feature Specification: Autonomous App Builder

**Feature Branch**: `002-autonomous-app-builder`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Plan: v0.5.0 — Autonomous App Builder — Enable 'Build me a stock app with AI using Microsoft tools' → agent asks 2-3 questions → creates everything → reports back. Extends existing app_service.py + pipeline orchestration with an app template library, GitHub repo import, an architect agent for IaC, and unified progress reporting across chat/voice/Signal."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversational App Building (Priority: P1)

As a user, I want to describe the app I want in natural language (e.g., "Build me a stock app with AI using Microsoft tools") and have the AI agent ask me 2-3 clarifying questions, present a build plan for my confirmation, and then autonomously create the entire app — so that I can go from idea to working scaffold without any manual setup.

**Why this priority**: This is the headline feature and primary value proposition of v0.5.0. It represents the complete end-to-end flow that all other stories support. Without this conversational builder experience, the individual components (templates, pipelines, progress) have limited standalone value.

**Independent Test**: Can be fully tested by typing "Build me a dashboard app" into the chat, answering 2-3 clarification questions, confirming the presented plan, and verifying that a new app appears in the Apps page with scaffolded files, a configured pipeline, and a launched initial issue.

**Acceptance Scenarios**:

1. **Given** a user types "Build me a stock tracking dashboard" in the chat, **When** the agent processes the request, **Then** the agent responds with 2-3 targeted clarifying questions about the app (e.g., preferred category, complexity level, deployment target).
2. **Given** a user has answered the clarifying questions, **When** the agent processes the answers, **Then** the agent presents a structured build plan showing the selected template, pipeline preset, estimated number of pipeline stages, and a confirmation prompt.
3. **Given** a user confirms the build plan, **When** the agent executes the build, **Then** the system creates a new app with template-scaffolded files, configures the appropriate pipeline, creates an initial parent issue, and launches the pipeline — all without further user input.
4. **Given** a user declines the build plan, **When** the agent processes the rejection, **Then** the agent asks what the user would like to change and presents an updated plan.

---

### User Story 2 - App Template Browsing and Selection (Priority: P1)

As a user, I want to browse a library of pre-built app templates (SaaS, API, CLI, Dashboard) and select one to create a new app — so that I can quickly start a project with a well-structured foundation instead of starting from scratch.

**Why this priority**: The template library is the foundational building block that powers the conversational builder (Story 1) and the frontend creation wizard. Without templates, there is no scaffold to generate. This is a prerequisite for all template-dependent features.

**Independent Test**: Can be fully tested by navigating to the template browser in the frontend, viewing the grid of available templates, filtering by category, and clicking "Use Template" on one to verify it starts the app creation flow.

**Acceptance Scenarios**:

1. **Given** a user navigates to the template browser, **When** the page loads, **Then** the user sees a grid of template cards showing at minimum: name, category, difficulty level, and a brief description for each of the four templates (SaaS, API, CLI, Dashboard).
2. **Given** a user filters templates by category (e.g., "dashboard"), **When** the filter is applied, **Then** only templates matching that category are displayed.
3. **Given** a user clicks "Use Template" on a template card, **When** the action is triggered, **Then** the user is taken to the app creation wizard pre-populated with that template's configuration.
4. **Given** a user clicks "Let AI configure" instead of manually selecting a template, **When** the action is triggered, **Then** the chat interface opens with context about the selected template, allowing the AI to guide configuration.

---

### User Story 3 - Build Progress Monitoring (Priority: P2)

As a user who has started an app build, I want to see real-time progress of the build process across chat, the frontend panel, and optionally Signal notifications — so that I know what stage the build is in, which agent is currently working, and when the build is complete.

**Why this priority**: Progress visibility is critical for user trust in an autonomous system. Without it, users have no feedback during what could be a multi-minute build process. However, the core build must work first (Story 1), so this is P2.

**Independent Test**: Can be fully tested by starting an app build and verifying that progress updates appear in the chat as status messages, a progress panel shows the current phase and agent, and a completion summary with links is displayed when the build finishes.

**Acceptance Scenarios**:

1. **Given** an app build is in progress, **When** the build transitions between phases (scaffolding → pipeline configuration → issue creation → pipeline execution), **Then** the user sees a progress update in the chat with the current phase name, active agent, and a progress indicator.
2. **Given** an app build is in progress, **When** the user views the frontend, **Then** a build progress panel shows a stepper or timeline view with completed, active, and pending phases.
3. **Given** an app build completes successfully, **When** the final phase finishes, **Then** the user receives a completion summary in the chat containing links to the created app, repository, and project board.
4. **Given** the user has Signal notifications enabled, **When** the build reaches milestone events (scaffolded, working, review-ready, complete), **Then** the user receives a Signal notification for each milestone.

---

### User Story 4 - GitHub Repository Import (Priority: P2)

As a user with an existing GitHub repository, I want to import it into Solune so that I can leverage Solune's pipeline orchestration, issue management, and AI agent capabilities on a project I've already started elsewhere.

**Why this priority**: Import provides an onramp for existing projects, expanding the user base beyond greenfield apps. It is independent of the template system and provides immediate value, but it is secondary to the core build-from-template flow.

**Independent Test**: Can be fully tested by entering a GitHub repository URL in the import form, validating it, and verifying that an app record is created in Solune with the repository linked and optionally a pipeline configured.

**Acceptance Scenarios**:

1. **Given** a user navigates to the "Import from GitHub" tab, **When** they enter a valid GitHub repository URL, **Then** the system validates the URL format and displays repository information (name, description, language) for confirmation.
2. **Given** a user confirms the import, **When** the import is executed, **Then** the system creates an app record linked to the external repository and optionally creates a GitHub Project V2 board for the app.
3. **Given** a user selects a pipeline during import, **When** the import completes, **Then** the system configures the selected pipeline for the imported app and is ready to run iteration cycles.
4. **Given** a user enters an invalid or inaccessible repository URL, **When** validation runs, **Then** the system displays a clear error message explaining why the URL is invalid (e.g., malformed URL, repository not found, insufficient permissions).

---

### User Story 5 - Iterate on Existing App (Priority: P3)

As a user with an existing app in Solune, I want to describe a change I want (e.g., "Add dark mode to the dashboard") and have the AI agent create an issue and launch a pipeline to implement it — so that I can continuously improve my app through natural language without manual issue and pipeline management.

**Why this priority**: Iteration support extends the app builder beyond initial creation. It is highly valuable for long-term engagement but depends on the core build flow (Story 1) being established first.

**Independent Test**: Can be fully tested by typing "Add user authentication to my dashboard app" in the chat, verifying that a new issue is created in the app's project, and confirming that a pipeline is launched to implement the change.

**Acceptance Scenarios**:

1. **Given** a user types "Add dark mode to my dashboard app" in the chat, **When** the agent processes the request, **Then** the agent identifies the target app, creates a new issue describing the change in the app's project board, and launches the appropriate pipeline.
2. **Given** a user requests a change to an app that does not exist, **When** the agent processes the request, **Then** the agent responds with a helpful message listing available apps or suggesting the user create one first.
3. **Given** a user requests a change and a pipeline is already running for that app, **When** the agent processes the request, **Then** the agent informs the user that a build is in progress and offers to queue the change for after completion.

---

### User Story 6 - Architect Agent for Infrastructure as Code (Priority: P3)

As a user building an app that requires deployment infrastructure, I want the build pipeline to automatically include an architect agent that generates Infrastructure as Code (IaC) artifacts — so that my app comes with deployment-ready configuration files without me having to write them manually.

**Why this priority**: IaC generation adds significant polish to the build output but is not essential for the core scaffolding and pipeline flow. It can be developed in parallel with the enhanced creation flow and integrated later.

**Independent Test**: Can be fully tested by building an app from a template that specifies an IaC target (e.g., Azure), verifying that the pipeline includes a "deploy-prep" stage with the architect agent, and confirming that the agent generates IaC files (e.g., Bicep, Terraform, docker-compose) in the app repository.

**Acceptance Scenarios**:

1. **Given** a user builds an app from a template with an IaC target of "azure," **When** the pipeline is configured, **Then** the pipeline includes a "deploy-prep" agent group containing the architect agent after the implementation stage.
2. **Given** the architect agent runs during the pipeline, **When** it processes the app's tech stack and IaC target metadata, **Then** it generates appropriate IaC files (e.g., Bicep templates, docker-compose files, GitHub Actions workflows) in the app's repository.
3. **Given** a user builds an app from a template with no IaC target, **When** the pipeline is configured, **Then** the pipeline does not include the architect agent or deploy-prep stage.

---

### Edge Cases

- What happens when a user requests an app type that does not match any available template? The agent should present the available templates and help the user choose the closest match or suggest using the import flow.
- What happens when template rendering encounters an undefined variable? The renderer should fail gracefully with a clear error identifying the missing variable rather than producing a partially rendered file.
- What happens when a user tries to import a private repository without sufficient permissions? The system should detect the permission issue during validation and display a message guiding the user to check their GitHub token permissions.
- What happens when WebSocket connection is lost during a build progress update? The frontend should attempt reconnection and, upon reconnection, fetch the current build state to resynchronize the progress display.
- What happens when a pipeline fails mid-build? The progress system should report the failure with details about which agent/phase failed, and the user should be able to retry or adjust and rebuild.
- What happens when two users simultaneously create apps with the same name? The system should enforce unique app names and return a clear error to the second user, suggesting an alternative name.
- What happens when the GitHub import URL points to an archived or empty repository? The system should detect this during validation and warn the user, allowing them to proceed if they choose.
- What happens when a template file contains path traversal sequences (e.g., `../../etc/passwd`)? The template renderer must validate all file paths and reject any that attempt to escape the app's directory boundary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an app template library containing at least four templates covering the categories: SaaS, API, CLI, and Dashboard.
- **FR-002**: System MUST define each template with the following metadata: identifier, name, category, difficulty level, technology stack description, scaffold type (skeleton or starter), file manifest, recommended pipeline preset, and IaC target.
- **FR-003**: System MUST provide a template rendering engine that populates template files with user-provided context variables using simple variable substitution.
- **FR-004**: System MUST validate all rendered file paths to prevent path traversal attacks — any path that escapes the target app directory must be rejected.
- **FR-005**: System MUST expose template browsing and detail retrieval as agent tools so the AI agent can list and inspect templates during conversation.
- **FR-006**: System MUST provide a GitHub repository import capability that validates a repository URL, creates an app record linked to the external repository, and optionally creates a GitHub Project V2 board.
- **FR-007**: System MUST expose the GitHub import capability as both an API endpoint and an agent tool.
- **FR-008**: System MUST extend the app creation flow to accept a template identifier and render template files as the initial scaffold instead of a minimal default.
- **FR-009**: System MUST automatically configure the appropriate pipeline preset based on the selected template and difficulty level.
- **FR-010**: System MUST insert the architect agent into the pipeline when the selected template specifies an IaC target.
- **FR-011**: System MUST provide an end-to-end orchestration tool that chains app creation, pipeline configuration, issue creation, and pipeline launch into a single operation.
- **FR-012**: System MUST provide an iteration tool that creates an issue in an existing app's project and launches the appropriate pipeline to implement the described change.
- **FR-013**: System MUST define an architect agent with a prompt focused on IaC generation (supporting Bicep, Terraform, docker-compose, and GitHub Actions).
- **FR-014**: System MUST register the architect agent in higher-difficulty pipeline presets as a "deploy-prep" stage following the implementation stage.
- **FR-015**: System MUST provide a build progress model that tracks the current phase, active agent name, detail text, and percentage complete.
- **FR-016**: System MUST emit build progress events via the existing WebSocket broadcast mechanism at each phase transition and agent assignment.
- **FR-017**: System MUST integrate build progress into the chat session by injecting status messages during the build and a final summary with links upon completion.
- **FR-018**: System MUST extend Signal notification delivery to send milestone notifications at key build stages (scaffolded, working, review-ready, complete).
- **FR-019**: System MUST provide a frontend build progress component that displays a stepper or timeline view and subscribes to WebSocket events for real-time updates.
- **FR-020**: System MUST extend the AI agent's instructions to recognize app-building intent (e.g., "build me an app"), trigger a clarification flow of 2-3 targeted questions, present a build plan for confirmation, and then execute the build.
- **FR-021**: System MUST provide a clarification question generation tool that produces 2-3 targeted questions based on the user's app description.
- **FR-022**: System MUST present a structured confirmation card showing the selected template, pipeline preset, and expected stages before executing a build.
- **FR-023**: System MUST recognize iteration intent (e.g., "add X to Y app") and invoke the iteration tool.
- **FR-024**: System MUST provide a frontend template browser with a grid layout, category filtering, and a "Use Template" action on each card.
- **FR-025**: System MUST provide a frontend app creation wizard that guides the user through template selection, app naming, customization, and creation.
- **FR-026**: System MUST provide a frontend GitHub import flow with URL input, validation feedback, repository info display, and import confirmation.
- **FR-027**: System MUST display structured build progress cards in chat messages showing phase, agent, and a progress indicator.

### Key Entities

- **App Template**: A reusable blueprint for creating a new app. Defined by an identifier, name, category (SaaS, API, CLI, Dashboard), difficulty level, technology stack description, scaffold type (skeleton for minimal structure or starter for working code), file manifest, recommended pipeline preset, and IaC target. Each template is stored as a directory containing a metadata definition and renderable file trees.
- **App (Extended)**: An application record in the system, extended to support both template-created apps and externally imported repositories. Includes a source type (template-created or external repository), a link to the originating template (if applicable), and a link to the external repository URL (if imported).
- **Build Progress**: A record of the current state of an app build operation. Tracks the active phase (scaffolding, configuring, issuing, building, deploying-prep, complete), the currently active agent name, a human-readable detail string, and a percentage complete indicator. Used to drive real-time progress display across chat, frontend, and notification channels.
- **Pipeline Preset Configuration**: A mapping from template category and difficulty level to a pipeline preset. Determines which agents participate in the pipeline and in what order. Includes logic to insert the architect agent when the template specifies an IaC target.
- **Architect Agent**: A specialized agent definition focused on generating Infrastructure as Code artifacts. Receives the app's technology stack and IaC target as context and produces deployment configuration files (Bicep, Terraform, docker-compose, GitHub Actions workflows).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from a natural language app description to a fully scaffolded app with a running pipeline in under 5 minutes of interaction time (excluding pipeline execution time).
- **SC-002**: 100% of app builds from templates produce a valid scaffold with all template files rendered and no rendering errors.
- **SC-003**: The system supports at least 4 distinct app templates across the SaaS, API, CLI, and Dashboard categories.
- **SC-004**: Users can import an existing GitHub repository and have it linked in Solune within 30 seconds.
- **SC-005**: Build progress updates are visible in the chat within 2 seconds of each phase transition.
- **SC-006**: 100% of builds for templates with an IaC target include the architect agent in the pipeline, and 100% of builds for templates without an IaC target exclude it.
- **SC-007**: The iteration flow (describing a change to an existing app) creates an issue and launches a pipeline without requiring the user to leave the chat interface.
- **SC-008**: Build milestone notifications are delivered via Signal within 10 seconds of the milestone event for users with Signal enabled.
- **SC-009**: The frontend template browser displays all available templates with accurate metadata and supports category filtering with zero-lag client-side filtering.
- **SC-010**: Template file path traversal attacks are blocked 100% of the time — no rendered file path may escape the target app directory.

## Assumptions

- v0.3.0 and v0.4.0 features are assumed to be shipped and stable, including the existing app_service.py, pipeline orchestration, WebSocket broadcasting, Signal delivery, and agent tools framework.
- Templates use a simple `{{variable}}` substitution syntax rather than a full templating engine. This is sufficient for the initial four templates and avoids introducing a new dependency.
- The architect agent generates IaC artifacts but does not perform actual cloud deployments. Deployment is explicitly out of scope for v0.5.0.
- GitHub repository import creates a link to the external repository — it does not clone or fork the repository. The imported app's pipeline operates on the linked repository.
- The clarification flow is limited to 2-3 questions to keep the conversation fast. The AI agent uses template metadata and the user's description to infer reasonable defaults for any unasked details.
- Pipeline preset selection is deterministic based on template category and difficulty — there is no user override of the preset in the initial implementation (though the "Let AI configure" path provides flexibility).
- Signal milestone notifications reuse the existing Signal delivery infrastructure and do not require a new integration or webhook setup.
- The frontend template browser, creation wizard, and import flow are new pages or components — they do not replace existing UI elements.
- Multi-repo apps, microservice orchestration, a template marketplace, and voice-specific app builder UX are explicitly out of scope for this version.
