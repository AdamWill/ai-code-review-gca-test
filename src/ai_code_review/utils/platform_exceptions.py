"""Platform-agnostic exceptions for code hosting platform operations."""

from __future__ import annotations

from ai_code_review.utils.exceptions import AICodeReviewError


class PlatformAPIError(AICodeReviewError):
    """Base exception for platform API errors."""

    def __init__(
        self,
        message: str,
        platform: str | None = None,
        response_code: int | None = None,
    ) -> None:
        """Initialize platform API error."""
        super().__init__(message)
        self.platform = platform
        self.response_code = response_code


class GitLabAPIError(PlatformAPIError):
    """GitLab API error (backward compatibility)."""

    def __init__(
        self,
        message: str,
        response_code: int | None = None,
    ) -> None:
        """Initialize GitLab API error."""
        super().__init__(message, platform="gitlab", response_code=response_code)


class GitHubAPIError(PlatformAPIError):
    """GitHub API error."""

    def __init__(
        self,
        message: str,
        response_code: int | None = None,
    ) -> None:
        """Initialize GitHub API error."""
        super().__init__(message, platform="github", response_code=response_code)


class GitLocalError(PlatformAPIError):
    """Local git operations error."""

    def __init__(self, message: str) -> None:
        """Initialize local git error."""
        super().__init__(message, platform="local", response_code=None)
