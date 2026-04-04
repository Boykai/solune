"""Tests for Azure infrastructure files — validates Bicep IaC, azd manifest,
ARM template, entrypoint script, and nginx template consistency.

Covers the following PR change areas:
- azure.yaml          — azd service manifest
- infra/main.bicep    — Bicep orchestrator
- infra/main.bicepparam — Bicep parameters
- infra/azuredeploy.json — compiled ARM template
- infra/modules/*.bicep — Bicep modules
- solune/frontend/entrypoint.sh — nginx startup script
- solune/frontend/nginx.conf — nginx template
- .github/workflows/deploy-azure.yml — CI/CD workflow
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import ClassVar

import pytest
import yaml

# Repository root — resolve relative to this test file.
REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_DIR = REPO_ROOT / "infra"
MODULES_DIR = INFRA_DIR / "modules"
FRONTEND_DIR = REPO_ROOT / "solune" / "frontend"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# azure.yaml — azd service manifest
# ---------------------------------------------------------------------------


class TestAzureYaml:
    """Validate azure.yaml structure and service definitions."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = REPO_ROOT / "azure.yaml"
        assert self.path.exists(), "azure.yaml not found at repo root"
        self.data = _load_yaml(self.path)

    def test_top_level_keys(self):
        assert self.data.get("name") == "solune"
        assert "services" in self.data
        assert "infra" in self.data

    def test_expected_services(self):
        services = self.data["services"]
        assert set(services.keys()) == {"backend", "frontend", "signal-api"}

    def test_backend_service(self):
        svc = self.data["services"]["backend"]
        assert svc["host"] == "containerapp"
        assert svc["docker"]["path"] == "Dockerfile"
        assert svc["project"] == "./solune/backend"
        assert "ca-backend-" in svc["resourceName"]

    def test_frontend_service(self):
        svc = self.data["services"]["frontend"]
        assert svc["host"] == "containerapp"
        assert svc["docker"]["path"] == "Dockerfile"
        assert svc["project"] == "./solune/frontend"
        assert "ca-frontend-" in svc["resourceName"]

    def test_signal_api_service(self):
        svc = self.data["services"]["signal-api"]
        assert svc["host"] == "containerapp"
        assert "signal-cli-rest-api" in svc["image"]
        assert "ca-signal-" in svc["resourceName"]

    def test_resource_name_pattern(self):
        """All resource names should use ${AZURE_ENV_NAME} variable."""
        for name, svc in self.data["services"].items():
            assert "${AZURE_ENV_NAME}" in svc["resourceName"], (
                f"Service '{name}' resourceName should contain ${{AZURE_ENV_NAME}}"
            )

    def test_infra_provider(self):
        infra = self.data["infra"]
        assert infra["provider"] == "bicep"
        assert infra["path"] == "infra"
        assert infra["module"] == "main"


# ---------------------------------------------------------------------------
# ARM template (azuredeploy.json) — compiled Bicep output
# ---------------------------------------------------------------------------


class TestArmTemplate:
    """Validate the compiled ARM template structure and parameters."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = INFRA_DIR / "azuredeploy.json"
        assert self.path.exists(), "infra/azuredeploy.json not found"
        self.data = _load_json(self.path)

    def test_schema_version(self):
        assert self.data["$schema"].startswith("https://schema.management.azure.com/schemas/")

    def test_content_version(self):
        assert self.data["contentVersion"] == "1.0.0.0"

    def test_required_parameters_present(self):
        params = set(self.data["parameters"].keys())
        expected = {
            "environmentName",
            "location",
            "githubClientId",
            "githubClientSecret",
            "sessionSecretKey",
            "encryptionKey",
            "adminGitHubUserId",
            "openAiModelName",
            "deployCapacity",
            "githubWebhookSecret",
        }
        assert expected.issubset(params), f"Missing parameters: {expected - params}"

    def test_secure_parameters(self):
        """Sensitive parameters must use securestring type."""
        params = self.data["parameters"]
        secure_params = {
            "githubClientSecret",
            "sessionSecretKey",
            "encryptionKey",
            "githubWebhookSecret",
        }
        for name in secure_params:
            assert params[name]["type"] == "securestring", (
                f"Parameter '{name}' must be securestring, got '{params[name]['type']}'"
            )

    def test_environment_name_constraints(self):
        env_param = self.data["parameters"]["environmentName"]
        assert env_param.get("minLength") == 1
        assert env_param.get("maxLength") == 20

    def test_has_resources(self):
        assert len(self.data["resources"]) >= 7, (
            "ARM template should have at least 7 module deployments"
        )

    def test_module_deployment_names(self):
        """Each nested deployment should match a known module name."""
        deploy_names = {r["name"] for r in self.data["resources"]}
        expected_modules = {
            "identity",
            "monitoring",
            "registry",
            "keyvault",
            "openai",
            "storage",
            "ai-foundry",
            "container-apps",
        }
        assert expected_modules.issubset(deploy_names), (
            f"Missing module deployments: {expected_modules - deploy_names}"
        )

    def test_expected_outputs(self):
        outputs = set(self.data["outputs"].keys())
        expected = {
            "frontendUrl",
            "backendInternalUrl",
            "signalApiInternalUrl",
            "keyVaultName",
            "openAiEndpoint",
            "oauthCallbackUrl",
        }
        assert expected.issubset(outputs), f"Missing outputs: {expected - outputs}"

    def test_no_plain_text_secrets_in_outputs(self):
        """Outputs should not contain the raw secret parameter references."""
        raw = json.dumps(self.data.get("outputs", {}))
        for secret_param in ("githubClientSecret", "sessionSecretKey", "encryptionKey"):
            assert f"parameters('{secret_param}')" not in raw, (
                f"Output references secret parameter '{secret_param}' directly"
            )

    def test_valid_json(self):
        """ARM template must be valid JSON (re-serialize to confirm)."""
        raw = self.path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Bicep files — structural validation
# ---------------------------------------------------------------------------


class TestBicepFiles:
    """Validate that all expected Bicep files exist and have basic structure."""

    EXPECTED_MODULES: ClassVar[list[str]] = [
        "identity.bicep",
        "monitoring.bicep",
        "registry.bicep",
        "keyvault.bicep",
        "openai.bicep",
        "storage.bicep",
        "ai-foundry.bicep",
        "container-apps.bicep",
    ]

    def test_main_bicep_exists(self):
        assert (INFRA_DIR / "main.bicep").exists()

    def test_main_bicepparam_exists(self):
        assert (INFRA_DIR / "main.bicepparam").exists()

    def test_all_modules_exist(self):
        for module in self.EXPECTED_MODULES:
            assert (MODULES_DIR / module).exists(), f"Module {module} not found"

    def test_main_bicep_references_all_modules(self):
        """main.bicep should reference every module file."""
        content = _read_text(INFRA_DIR / "main.bicep")
        for module in self.EXPECTED_MODULES:
            assert f"modules/{module}" in content, f"main.bicep does not reference modules/{module}"

    def test_main_bicep_target_scope(self):
        content = _read_text(INFRA_DIR / "main.bicep")
        assert "targetScope = 'resourceGroup'" in content

    def test_main_bicep_has_outputs(self):
        content = _read_text(INFRA_DIR / "main.bicep")
        assert content.count("output ") >= 10, "main.bicep should have at least 10 outputs"

    def test_bicepparam_references_main(self):
        content = _read_text(INFRA_DIR / "main.bicepparam")
        assert "using './main.bicep'" in content

    def test_bicepparam_has_all_parameters(self):
        """main.bicepparam should set all required parameters."""
        content = _read_text(INFRA_DIR / "main.bicepparam")
        required = [
            "environmentName",
            "location",
            "githubClientId",
            "githubClientSecret",
            "sessionSecretKey",
            "encryptionKey",
            "adminGitHubUserId",
            "githubWebhookSecret",
        ]
        for param in required:
            assert f"param {param}" in content, f"main.bicepparam missing param {param}"


# ---------------------------------------------------------------------------
# Bicep cross-file consistency
# ---------------------------------------------------------------------------


class TestBicepCrossFileConsistency:
    """Validate naming conventions and resource references across Bicep files."""

    def test_container_app_names_match_azure_yaml(self):
        """Container app names in Bicep should match azure.yaml resourceName patterns."""
        bicep_content = _read_text(MODULES_DIR / "container-apps.bicep")
        azure_yaml = _load_yaml(REPO_ROOT / "azure.yaml")

        # Extract Bicep container app name patterns
        bicep_names = re.findall(r"name:\s*'(ca-\w+-\$\{environmentName\})'", bicep_content)
        assert len(bicep_names) >= 3, (
            f"Expected at least 3 container app names in Bicep, found {len(bicep_names)}"
        )

        # Extract azure.yaml resource name prefixes (before ${AZURE_ENV_NAME})
        for svc_name, svc in azure_yaml["services"].items():
            prefix = svc["resourceName"].split("${AZURE_ENV_NAME}")[0]
            matching = [n for n in bicep_names if prefix.rstrip("-") in n]
            assert matching, (
                f"azure.yaml service '{svc_name}' prefix '{prefix}' not found in Bicep container app names"
            )

    def test_keyvault_secret_names_match(self):
        """Secret names in keyvault.bicep should match secret refs in container-apps.bicep."""
        kv_content = _read_text(MODULES_DIR / "keyvault.bicep")
        ca_content = _read_text(MODULES_DIR / "container-apps.bicep")

        # Extract secret names from keyvault.bicep
        kv_secrets = set(re.findall(r"name:\s*'([a-z-]+)'\s*\n\s*properties:", kv_content))
        # Extract keyVaultUrl secret references from container-apps.bicep
        ca_secrets = set(re.findall(r"/secrets/([a-z-]+)'", ca_content))

        assert ca_secrets, "No Key Vault secret references found in container-apps.bicep"
        assert ca_secrets.issubset(kv_secrets), (
            f"Container apps reference secrets not defined in Key Vault: {ca_secrets - kv_secrets}"
        )

    def test_storage_share_names_match(self):
        """File share names in storage.bicep should match volume mounts in container-apps.bicep."""
        storage_content = _read_text(MODULES_DIR / "storage.bicep")
        ca_content = _read_text(MODULES_DIR / "container-apps.bicep")

        # Extract share names from storage.bicep
        storage_shares = set(re.findall(r"name:\s*'(solune-data|signal-config)'", storage_content))
        # Extract share references from container-apps.bicep
        ca_shares = set(re.findall(r"shareName:\s*'([\w-]+)'", ca_content))

        assert storage_shares == ca_shares, (
            f"Storage shares {storage_shares} don't match container app shares {ca_shares}"
        )

    def test_identity_module_outputs_used(self):
        """identity.bicep outputs should be consumed in main.bicep."""
        main_content = _read_text(INFRA_DIR / "main.bicep")
        identity_content = _read_text(MODULES_DIR / "identity.bicep")

        # Extract output names from identity.bicep
        outputs = re.findall(r"output\s+(\w+)\s+", identity_content)
        assert len(outputs) >= 3, "identity.bicep should have at least 3 outputs"

        for output_name in outputs:
            assert f"identity.outputs.{output_name}" in main_content, (
                f"identity.bicep output '{output_name}' not used in main.bicep"
            )

    def test_health_probe_paths(self):
        """Health probe paths should match expected service endpoints."""
        ca_content = _read_text(MODULES_DIR / "container-apps.bicep")

        assert "'/api/v1/health'" in ca_content, "Backend health probe path missing"
        assert "'/health'" in ca_content, "Frontend health probe path missing"
        assert "'/v1/health'" in ca_content, "Signal API health probe path missing"

    def test_no_hardcoded_secrets_in_env_vars(self):
        """Container app env vars should not contain hardcoded secret values."""
        ca_content = _read_text(MODULES_DIR / "container-apps.bicep")

        # Env vars that should use secretRef, not value
        secret_env_vars = [
            "GITHUB_CLIENT_ID",
            "GITHUB_CLIENT_SECRET",
            "SESSION_SECRET_KEY",
            "ENCRYPTION_KEY",
            "GITHUB_WEBHOOK_SECRET",
            "AZURE_OPENAI_KEY",
        ]
        for var_name in secret_env_vars:
            # Find the env var block — should use secretRef, not a direct value with the param
            pattern = rf"\{{\s*name:\s*'{var_name}'\s*,\s*secretRef:"
            assert re.search(pattern, ca_content), (
                f"Env var '{var_name}' should use secretRef (Key Vault reference), not a plain value"
            )


# ---------------------------------------------------------------------------
# Bicep module-level validation
# ---------------------------------------------------------------------------


class TestBicepModuleStructure:
    """Validate individual Bicep module structure and security properties."""

    def test_keyvault_purge_protection(self):
        content = _read_text(MODULES_DIR / "keyvault.bicep")
        assert "enablePurgeProtection: true" in content

    def test_keyvault_rbac_authorization(self):
        content = _read_text(MODULES_DIR / "keyvault.bicep")
        assert "enableRbacAuthorization: true" in content

    def test_keyvault_soft_delete(self):
        content = _read_text(MODULES_DIR / "keyvault.bicep")
        assert "softDeleteRetentionInDays: 90" in content

    def test_storage_tls_12(self):
        content = _read_text(MODULES_DIR / "storage.bicep")
        assert "minimumTlsVersion: 'TLS1_2'" in content

    def test_storage_https_only(self):
        content = _read_text(MODULES_DIR / "storage.bicep")
        assert "supportsHttpsTrafficOnly: true" in content

    def test_storage_no_public_blob_access(self):
        content = _read_text(MODULES_DIR / "storage.bicep")
        assert "allowBlobPublicAccess: false" in content

    def test_registry_admin_disabled(self):
        content = _read_text(MODULES_DIR / "registry.bicep")
        assert "adminUserEnabled: false" in content

    def test_backend_internal_ingress(self):
        """Backend should use internal ingress (not publicly accessible)."""
        content = _read_text(MODULES_DIR / "container-apps.bicep")
        # Find backend app ingress — external: false
        backend_section = content[: content.index("Frontend Container App")]
        assert "external: false" in backend_section

    def test_frontend_external_ingress(self):
        """Frontend should use external ingress (publicly accessible)."""
        content = _read_text(MODULES_DIR / "container-apps.bicep")
        frontend_section = content[content.index("Frontend Container App") :]
        signal_idx = frontend_section.index("Signal API Container App")
        frontend_only = frontend_section[:signal_idx]
        assert "external: true" in frontend_only

    def test_signal_api_internal_ingress(self):
        """Signal API should use internal ingress."""
        content = _read_text(MODULES_DIR / "container-apps.bicep")
        signal_section = content[content.index("Signal API Container App") :]
        assert "external: false" in signal_section

    def test_backend_ai_provider_azure(self):
        """Backend should be configured with AI_PROVIDER=azure_openai."""
        content = _read_text(MODULES_DIR / "container-apps.bicep")
        assert "{ name: 'AI_PROVIDER', value: 'azure_openai' }" in content

    def test_backend_cookie_secure(self):
        """Backend should have COOKIE_SECURE=true in Azure deployment."""
        content = _read_text(MODULES_DIR / "container-apps.bicep")
        assert "{ name: 'COOKIE_SECURE', value: 'true' }" in content

    def test_openai_model_gpt4o(self):
        """OpenAI module should deploy gpt-4o model."""
        content = _read_text(MODULES_DIR / "openai.bicep")
        assert "name: 'gpt-4o'" in content


# ---------------------------------------------------------------------------
# RBAC role assignments
# ---------------------------------------------------------------------------


class TestRbacRoleAssignments:
    """Validate that all required RBAC role IDs are present across modules."""

    # Well-known Azure role definition IDs
    EXPECTED_ROLES: ClassVar[dict[str, str]] = {
        "AcrPull": "7f951dda-4ed3-4680-a7ca-43fe172d538d",
        "Key Vault Secrets User": "4633458b-17de-408a-b874-0445c86b69e6",
        "Cognitive Services OpenAI User": "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd",
        "Azure AI Developer": "64702f94-c441-49e6-a78b-ef80e0188fee",
        "Storage File Data SMB Share Contributor": "0c867c2a-1d8c-454a-a3db-ab2ea1bdc8bb",
    }

    def test_all_required_roles_assigned(self):
        """Each expected RBAC role ID should appear in at least one module."""
        all_module_content = ""
        for bicep_file in MODULES_DIR.glob("*.bicep"):
            all_module_content += _read_text(bicep_file)

        for role_name, role_id in self.EXPECTED_ROLES.items():
            assert role_id in all_module_content, (
                f"RBAC role '{role_name}' (ID: {role_id}) not found in any Bicep module"
            )

    def test_role_assignments_use_service_principal_type(self):
        """All role assignments should set principalType to ServicePrincipal."""
        for bicep_file in MODULES_DIR.glob("*.bicep"):
            content = _read_text(bicep_file)
            role_assignments = re.findall(
                r"resource\s+\w+\s+'Microsoft\.Authorization/roleAssignments", content
            )
            if role_assignments:
                assert "principalType: 'ServicePrincipal'" in content, (
                    f"{bicep_file.name} has role assignments but missing principalType: 'ServicePrincipal'"
                )


# ---------------------------------------------------------------------------
# Frontend entrypoint.sh — startup script behavior
# ---------------------------------------------------------------------------


class TestEntrypointScript:
    """Validate the nginx entrypoint script behavior."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script_path = FRONTEND_DIR / "entrypoint.sh"
        assert self.script_path.exists(), "entrypoint.sh not found"
        self.content = _read_text(self.script_path)

    def test_shebang(self):
        assert self.content.startswith("#!/bin/sh")

    def test_default_backend_origin(self):
        """Should default to http://backend:8000 for docker-compose compatibility."""
        assert "BACKEND_ORIGIN:-http://backend:8000" in self.content

    def test_validates_url_scheme(self):
        """Should validate BACKEND_ORIGIN starts with http:// or https://."""
        assert "http://*|https://*" in self.content

    def test_rejects_invalid_scheme(self):
        """Should exit with error for invalid BACKEND_ORIGIN."""
        assert "exit 1" in self.content
        assert "ERROR" in self.content

    def test_uses_envsubst(self):
        """Should use envsubst to substitute BACKEND_ORIGIN into nginx config."""
        assert "envsubst" in self.content
        assert "BACKEND_ORIGIN" in self.content
        assert "default.conf.template" in self.content

    def test_execs_nginx(self):
        """Should exec nginx (not fork) to be PID 1."""
        assert "exec nginx" in self.content

    def test_valid_shell_accepts_http(self):
        """entrypoint.sh validation logic should accept http:// URLs."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                """
                export BACKEND_ORIGIN="http://backend:8000"
                case "$BACKEND_ORIGIN" in
                  http://*|https://*) echo "OK" ;;
                  *) echo "FAIL"; exit 1 ;;
                esac
            """,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_valid_shell_accepts_https(self):
        """entrypoint.sh validation logic should accept https:// URLs."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                """
                export BACKEND_ORIGIN="https://ca-backend-prod.internal.myenv.azurecontainerapps.io"
                case "$BACKEND_ORIGIN" in
                  http://*|https://*) echo "OK" ;;
                  *) echo "FAIL"; exit 1 ;;
                esac
            """,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_valid_shell_rejects_ftp(self):
        """entrypoint.sh validation logic should reject ftp:// URLs."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                """
                export BACKEND_ORIGIN="ftp://evil.example.com"
                case "$BACKEND_ORIGIN" in
                  http://*|https://*) echo "OK" ;;
                  *) echo "FAIL"; exit 1 ;;
                esac
            """,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1

    def test_valid_shell_rejects_empty(self):
        """entrypoint.sh validation logic should reject empty strings."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                """
                export BACKEND_ORIGIN=""
                case "$BACKEND_ORIGIN" in
                  http://*|https://*) echo "OK" ;;
                  *) echo "FAIL"; exit 1 ;;
                esac
            """,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1

    def test_valid_shell_rejects_bare_hostname(self):
        """entrypoint.sh validation logic should reject bare hostnames."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                """
                export BACKEND_ORIGIN="backend:8000"
                case "$BACKEND_ORIGIN" in
                  http://*|https://*) echo "OK" ;;
                  *) echo "FAIL"; exit 1 ;;
                esac
            """,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1


# ---------------------------------------------------------------------------
# nginx.conf — template placeholders
# ---------------------------------------------------------------------------


class TestNginxConfig:
    """Validate the nginx configuration template."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = FRONTEND_DIR / "nginx.conf"
        assert self.path.exists(), "nginx.conf not found"
        self.content = _read_text(self.path)

    def test_backend_origin_placeholder(self):
        """nginx.conf should use ${BACKEND_ORIGIN} for the proxy_pass directive."""
        assert "${BACKEND_ORIGIN}/api/" in self.content

    def test_no_hardcoded_backend_url(self):
        """nginx.conf should not hardcode http://backend:8000."""
        assert "http://backend:8000" not in self.content

    def test_health_endpoint(self):
        assert "location /health" in self.content
        assert 'return 200 "OK"' in self.content

    def test_websocket_support(self):
        assert "proxy_set_header Upgrade" in self.content
        assert "proxy_set_header Connection" in self.content

    def test_security_headers(self):
        assert "X-Frame-Options" in self.content
        assert "X-Content-Type-Options" in self.content
        assert "Strict-Transport-Security" in self.content
        assert "Content-Security-Policy" in self.content

    def test_server_tokens_off(self):
        assert "server_tokens off" in self.content

    def test_listens_on_8080(self):
        assert "listen 8080" in self.content

    def test_spa_fallback(self):
        """SPA apps need a fallback to index.html for client-side routing."""
        assert "try_files" in self.content
        assert "/index.html" in self.content

    def test_gzip_enabled(self):
        assert "gzip on" in self.content


# ---------------------------------------------------------------------------
# Dockerfile — entrypoint integration
# ---------------------------------------------------------------------------


class TestDockerfile:
    """Validate the frontend Dockerfile references entrypoint.sh correctly."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = FRONTEND_DIR / "Dockerfile"
        assert self.path.exists(), "Dockerfile not found"
        self.content = _read_text(self.path)

    def test_copies_nginx_conf_as_template(self):
        """nginx.conf should be copied as .template for envsubst."""
        assert "default.conf.template" in self.content

    def test_copies_entrypoint(self):
        assert "entrypoint.sh" in self.content

    def test_entrypoint_executable(self):
        assert "chmod +x /entrypoint.sh" in self.content

    def test_cmd_uses_entrypoint(self):
        assert "/entrypoint.sh" in self.content

    def test_healthcheck_present(self):
        assert "HEALTHCHECK" in self.content
        assert "localhost:8080/health" in self.content

    def test_non_root_user(self):
        assert "USER nginx-app" in self.content


# ---------------------------------------------------------------------------
# GitHub Actions workflow — deploy-azure.yml
# ---------------------------------------------------------------------------


class TestDeployWorkflow:
    """Validate the GitHub Actions deployment workflow."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = REPO_ROOT / ".github" / "workflows" / "deploy-azure.yml"
        assert self.path.exists(), "deploy-azure.yml not found"
        self.data = _load_yaml(self.path)
        self.content = _read_text(self.path)

    def test_workflow_dispatch_trigger(self):
        # PyYAML parses YAML key `on:` as Python boolean True.
        triggers = self.data.get(True, {})
        assert "workflow_dispatch" in triggers

    def test_oidc_permissions(self):
        """Workflow should request id-token: write for OIDC auth."""
        perms = self.data.get("permissions", {})
        assert perms.get("id-token") == "write"
        assert perms.get("contents") == "read"

    def test_uses_azd(self):
        assert "Azure/setup-azd" in self.content

    def test_provisions_and_deploys(self):
        assert "azd provision" in self.content
        assert "azd deploy" in self.content

    def test_no_hardcoded_secrets(self):
        """Workflow should not contain any hardcoded secret values."""
        # Check for common secret patterns
        assert "AKIA" not in self.content  # AWS keys
        assert "ghp_" not in self.content  # GitHub PATs
        assert "sk-" not in self.content  # OpenAI keys

    def test_required_secrets_referenced(self):
        """Workflow should reference required secrets."""
        required_secrets = [
            "AZURE_CLIENT_ID",
            "AZURE_TENANT_ID",
            "AZURE_SUBSCRIPTION_ID",
        ]
        for secret in required_secrets:
            assert secret in self.content, f"Workflow should reference secret '{secret}'"

    def test_checkout_step(self):
        assert "actions/checkout@v4" in self.content


# ---------------------------------------------------------------------------
# README.md — Deploy button
# ---------------------------------------------------------------------------


class TestReadmeDeployButton:
    """Validate the README Azure deployment section."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = REPO_ROOT / "README.md"
        assert self.path.exists()
        self.content = _read_text(self.path)

    def test_deploy_button_present(self):
        assert "Deploy to Azure" in self.content

    def test_deploy_button_url_format(self):
        """Deploy button URL should point to Azure portal with ARM template."""
        assert "portal.azure.com/#create/Microsoft.Template/uri/" in self.content

    def test_deploy_button_references_arm_template(self):
        """Deploy button should reference the azuredeploy.json file."""
        assert "azuredeploy.json" in self.content

    def test_azure_deployment_section(self):
        assert "## Azure Deployment" in self.content

    def test_prerequisites_section(self):
        assert "Prerequisites" in self.content

    def test_azd_cli_alternative(self):
        assert "azd" in self.content

    def test_post_deployment_instructions(self):
        assert "Post-Deployment" in self.content
        assert "callback" in self.content.lower()
