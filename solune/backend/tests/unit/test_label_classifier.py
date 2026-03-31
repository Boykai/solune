from src.services.completion_providers import CompletionProvider
from src.services.label_classifier import classify_labels, validate_labels


class MockCompletionProvider(CompletionProvider):
    def __init__(self, response: str = "", *, error: Exception | None = None):
        self._response = response
        self._error = error

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        github_token: str | None = None,
    ) -> str:
        if self._error is not None:
            raise self._error
        return self._response

    @property
    def name(self) -> str:
        return "mock"


class TestValidateLabels:
    def test_filters_invalid_labels_and_adds_defaults(self):
        labels = validate_labels(["Backend", "unknown", "bug", "bug"])
        assert labels == ["ai-generated", "backend", "bug"]

    def test_adds_default_type_when_missing(self):
        labels = validate_labels(["security"])
        assert labels == ["ai-generated", "security", "feature"]


class TestClassifyLabels:
    async def test_parses_json_response(self):
        labels = await classify_labels(
            "Fix login API",
            "Backend returns 500 when credentials are valid.",
            github_token="token",
            provider=MockCompletionProvider('{"labels":["bug","backend","invalid"]}'),
        )

        assert labels == ["ai-generated", "bug", "backend"]

    async def test_falls_back_when_provider_errors(self):
        labels = await classify_labels(
            "Ship docs",
            "Document the setup flow.",
            github_token="token",
            provider=MockCompletionProvider(error=RuntimeError("boom")),
        )

        assert labels == ["ai-generated", "feature"]

    async def test_falls_back_when_token_missing(self):
        labels = await classify_labels(
            "Ship docs",
            "Document the setup flow.",
            github_token=None,
        )

        assert labels == ["ai-generated", "feature"]
