"""Custom exceptions for AI Code Review tool."""

from __future__ import annotations

# Exit codes for different scenarios
EXIT_CODE_SUCCESS = 0
EXIT_CODE_GENERAL_ERROR = 1
EXIT_CODE_PLATFORM_ERROR = 2  # GitLab/GitHub API errors
EXIT_CODE_AI_PROVIDER_ERROR = 3  # AI provider errors
EXIT_CODE_TIMEOUT_ERROR = 4  # Timeout errors
EXIT_CODE_EMPTY_MR = 5  # Empty merge request (no changes)
EXIT_CODE_SKIPPED = 6  # Review was skipped automatically


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


class ReviewSkippedError(AICodeReviewError):
    """Exception raised when a review is automatically skipped."""

    def __init__(self, message: str, reason: str, trigger: str) -> None:
        """Initialize review skipped error.

        Args:
            message: Human-readable message describing why review was skipped
            reason: Category of skip reason (keyword, pattern, bot_author, etc.)
            trigger: Specific trigger that caused the skip (pattern text, keyword, etc.)
        """
        super().__init__(message)
        self.reason = reason
        self.trigger = trigger
