"""Tests for custom application exceptions (src/exceptions.py)."""

from src.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    GitHubAPIError,
    McpLimitExceededError,
    McpValidationError,
    NotFoundError,
    PersistenceError,
    RateLimitError,
    ValidationError,
)


class TestAppException:
    def test_default_status_code(self):
        exc = AppException("something broke")
        assert exc.message == "something broke"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_custom_status_code(self):
        exc = AppException("bad", status_code=418)
        assert exc.status_code == 418

    def test_custom_details(self):
        exc = AppException("oops", details={"field": "name"})
        assert exc.details == {"field": "name"}

    def test_string_representation(self):
        exc = AppException("failure")
        assert str(exc) == "failure"


class TestAuthenticationError:
    def test_default_message(self):
        exc = AuthenticationError()
        assert exc.message == "Authentication required"
        assert exc.status_code == 401

    def test_custom_message(self):
        exc = AuthenticationError("Token expired")
        assert exc.message == "Token expired"
        assert exc.status_code == 401


class TestAuthorizationError:
    def test_default_message(self):
        exc = AuthorizationError()
        assert exc.message == "Access denied"
        assert exc.status_code == 403

    def test_custom_message(self):
        exc = AuthorizationError("Insufficient permissions")
        assert exc.message == "Insufficient permissions"


class TestNotFoundError:
    def test_default_message(self):
        exc = NotFoundError()
        assert exc.message == "Resource not found"
        assert exc.status_code == 404

    def test_custom_message(self):
        exc = NotFoundError("Project not found")
        assert exc.message == "Project not found"


class TestValidationError:
    def test_basic_message(self):
        exc = ValidationError("Invalid input")
        assert exc.message == "Invalid input"
        assert exc.status_code == 422
        assert exc.details == {}

    def test_with_details(self):
        exc = ValidationError("Bad data", details={"field": "email"})
        assert exc.details == {"field": "email"}


class TestGitHubAPIError:
    def test_basic_message(self):
        exc = GitHubAPIError("API failure")
        assert exc.message == "API failure"
        assert exc.status_code == 502

    def test_with_details(self):
        exc = GitHubAPIError("Rate limited", details={"retry_after": 60})
        assert exc.details == {"retry_after": 60}


class TestRateLimitError:
    def test_default_retry_after(self):
        exc = RateLimitError()
        assert exc.message == "Rate limit exceeded"
        assert exc.status_code == 429
        assert exc.retry_after == 60

    def test_custom_retry_after(self):
        exc = RateLimitError("Slow down", retry_after=120)
        assert exc.retry_after == 120


class TestExceptionInheritance:
    def test_all_inherit_from_app_exception(self):
        assert issubclass(AuthenticationError, AppException)
        assert issubclass(AuthorizationError, AppException)
        assert issubclass(NotFoundError, AppException)
        assert issubclass(ValidationError, AppException)
        assert issubclass(GitHubAPIError, AppException)
        assert issubclass(RateLimitError, AppException)

    def test_all_inherit_from_exception(self):
        assert issubclass(AppException, Exception)


class TestConflictError:
    def test_default_message(self):
        exc = ConflictError()
        assert exc.message == "Resource conflict"
        assert exc.status_code == 409

    def test_custom_message_and_details(self):
        exc = ConflictError("Duplicate name", details={"name": "existing"})
        assert exc.message == "Duplicate name"
        assert exc.details == {"name": "existing"}


class TestMcpValidationError:
    def test_basic_message(self):
        exc = McpValidationError("Invalid URL")
        assert exc.message == "Invalid URL"
        assert exc.status_code == 400
        assert exc.field_errors == {}
        assert exc.details == {}

    def test_with_field_errors(self):
        field_errors = {
            "url": ["URL must be HTTPS", "URL is unreachable"],
            "name": ["Name is required"],
        }
        exc = McpValidationError("Validation failed", field_errors=field_errors)
        assert exc.field_errors == field_errors
        assert exc.details == {"field_errors": field_errors}

    def test_backward_compatible_positional_message(self):
        """Existing callers that only pass message should still work."""
        exc = McpValidationError("SSRF detected")
        assert exc.message == "SSRF detected"
        assert exc.field_errors == {}

    def test_inherits_from_app_exception(self):
        assert issubclass(McpValidationError, AppException)


class TestMcpLimitExceededError:
    def test_basic_message(self):
        exc = McpLimitExceededError("Too many MCPs")
        assert exc.message == "Too many MCPs"
        assert exc.status_code == 409

    def test_inherits_from_app_exception(self):
        assert issubclass(McpLimitExceededError, AppException)


class TestDatabaseError:
    def test_default_message(self):
        exc = DatabaseError()
        assert exc.message == "Database error"
        assert exc.status_code == 500

    def test_custom_details(self):
        exc = DatabaseError("Failed query", details={"query": "SELECT *"})
        assert exc.details == {"query": "SELECT *"}


class TestPersistenceError:
    def test_default_message(self):
        exc = PersistenceError()
        assert exc.message == "Persistence failed"
        assert exc.status_code == 500

    def test_inherits_from_database_error(self):
        assert issubclass(PersistenceError, DatabaseError)
