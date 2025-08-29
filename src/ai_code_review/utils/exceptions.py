"""Custom exceptions for AI Code Review tool."""

from __future__ import annotations


class AICodeReviewError(Exception):
    """Base exception for AI Code Review tool."""

    pass


class GitLabAPIError(AICodeReviewError):
    """Exception raised when GitLab API operations fail."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize GitLab API error."""
        super().__init__(message)
        self.status_code = status_code


class AIProviderError(AICodeReviewError):
    """Exception raised when AI provider operations fail."""

    def __init__(self, message: str, provider: str) -> None:
        """Initialize AI provider error."""
        super().__init__(message)
        self.provider = provider


class ConfigurationError(AICodeReviewError):
    """Exception raised when configuration is invalid."""

    pass


class ContentTooLargeError(AICodeReviewError):
    """Exception raised when content exceeds size limits."""

    def __init__(self, message: str, current_size: int, max_size: int) -> None:
        """Initialize content too large error."""
        super().__init__(message)
        self.current_size = current_size
        self.max_size = max_size
