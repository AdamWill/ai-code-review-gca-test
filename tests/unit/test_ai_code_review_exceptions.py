"""Tests for custom exceptions."""

from __future__ import annotations

import pytest

from ai_code_review.utils.exceptions import (
    AICodeReviewError,
    AIProviderError,
    ConfigurationError,
    ContentTooLargeError,
    GitLabAPIError,
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_ai_code_review_error_creation(self) -> None:
        """Test AICodeReviewError basic creation."""
        error = AICodeReviewError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_ai_provider_error_creation(self) -> None:
        """Test AIProviderError creation with provider info."""
        error = AIProviderError("Connection failed", "anthropic")

        assert str(error) == "Connection failed"
        assert error.provider == "anthropic"
        assert isinstance(error, AICodeReviewError)

    def test_gitlab_api_error_creation(self) -> None:
        """Test GitLabAPIError creation."""
        error = GitLabAPIError("API request failed", 404)

        assert str(error) == "API request failed"
        assert error.status_code == 404
        assert isinstance(error, AICodeReviewError)

    def test_configuration_error_creation(self) -> None:
        """Test ConfigurationError creation."""
        error = ConfigurationError("Invalid config")

        assert str(error) == "Invalid config"
        assert isinstance(error, AICodeReviewError)

    def test_content_too_large_error_creation(self) -> None:
        """Test ContentTooLargeError creation with size info."""
        error = ContentTooLargeError("Content exceeds limit", 150000, 100000)

        assert str(error) == "Content exceeds limit"
        assert error.current_size == 150000
        assert error.max_size == 100000
        assert isinstance(error, AICodeReviewError)

    def test_exceptions_can_be_raised(self) -> None:
        """Test that exceptions can be properly raised and caught."""
        with pytest.raises(AIProviderError) as exc_info:
            raise AIProviderError("Test provider error", "test")

        assert exc_info.value.provider == "test"
        assert str(exc_info.value) == "Test provider error"

        with pytest.raises(ContentTooLargeError) as exc_info:
            raise ContentTooLargeError("Too big", 200, 100)

        assert exc_info.value.current_size == 200
        assert exc_info.value.max_size == 100

        with pytest.raises(GitLabAPIError) as exc_info:
            raise GitLabAPIError("GitLab failed", 500)

        assert exc_info.value.status_code == 500
