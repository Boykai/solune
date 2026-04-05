"""Tests for the templates API endpoints."""

from unittest.mock import patch

from src.models.app_template import AppCategory, AppTemplate, IaCTarget, ScaffoldType, TemplateFile

MEDIUM_DIFFICULTY = "M"


def _template(template_id: str = "saas-react-fastapi", *, category: AppCategory = AppCategory.SAAS) -> AppTemplate:
    return AppTemplate(
        id=template_id,
        name="SaaS — React + FastAPI",
        description="Full-stack starter",
        category=category,
        difficulty=MEDIUM_DIFFICULTY,
        tech_stack=["react", "fastapi"],
        scaffold_type=ScaffoldType.STARTER,
        files=[
            TemplateFile(
                source="template.json",
                target="template.json",
                variables=["project_name"],
            )
        ],
        recommended_preset_id="preset-fullstack",
        iac_target=IaCTarget.DOCKER,
    )


class TestListTemplatesEndpoint:
    async def test_empty_registry_returns_empty_list(self, client):
        with patch("src.api.templates.list_templates", return_value=[]) as mock_list:
            response = await client.get("/api/v1/templates")

        assert response.status_code == 200
        assert response.json() == []
        mock_list.assert_called_once_with(category=None)

    async def test_invalid_category_returns_400(self, client):
        response = await client.get("/api/v1/templates?category=invalid")

        assert response.status_code == 400
        assert "Invalid category: invalid" in response.json()["detail"]

    async def test_list_returns_summary_fields_only(self, client):
        template = _template()

        with patch("src.api.templates.list_templates", return_value=[template]):
            response = await client.get("/api/v1/templates")

        assert response.status_code == 200
        assert response.json() == [
            {
                "id": "saas-react-fastapi",
                "name": "SaaS — React + FastAPI",
                "description": "Full-stack starter",
                "category": "saas",
                "difficulty": MEDIUM_DIFFICULTY,
                "tech_stack": ["react", "fastapi"],
                "scaffold_type": "starter",
                "iac_target": "docker",
            }
        ]
        assert "files" not in response.json()[0]
        assert "recommended_preset_id" not in response.json()[0]

    async def test_list_passes_valid_category_filter(self, client):
        template = _template(template_id="api-fastapi", category=AppCategory.API)

        with patch("src.api.templates.list_templates", return_value=[template]) as mock_list:
            response = await client.get("/api/v1/templates?category=api")

        assert response.status_code == 200
        mock_list.assert_called_once_with(category=AppCategory.API)


class TestGetTemplateEndpoint:
    async def test_detail_returns_file_manifest_and_recommended_preset(self, client):
        template = _template()

        with patch("src.api.templates.get_template", return_value=template):
            response = await client.get("/api/v1/templates/saas-react-fastapi")

        assert response.status_code == 200
        assert response.json() == {
            "id": "saas-react-fastapi",
            "name": "SaaS — React + FastAPI",
            "description": "Full-stack starter",
            "category": "saas",
            "difficulty": MEDIUM_DIFFICULTY,
            "tech_stack": ["react", "fastapi"],
            "scaffold_type": "starter",
            "iac_target": "docker",
            "files": [
                {
                    "source": "template.json",
                    "target": "template.json",
                    "variables": ["project_name"],
                }
            ],
            "recommended_preset_id": "preset-fullstack",
        }

    async def test_detail_returns_404_when_template_missing(self, client):
        with patch("src.api.templates.get_template", return_value=None):
            response = await client.get("/api/v1/templates/missing-template")

        assert response.status_code == 404
        assert response.json()["detail"] == "Template not found"
