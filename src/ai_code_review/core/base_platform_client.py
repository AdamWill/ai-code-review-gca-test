"""Base platform client implementation."""

from __future__ import annotations

import fnmatch
from abc import ABC, abstractmethod
from pathlib import PurePath

from ai_code_review.models.config import Config
from ai_code_review.models.platform import (
    PlatformClientInterface,
    PostReviewResponse,
    PullRequestData,
    PullRequestDiff,
)


class BasePlatformClient(PlatformClientInterface, ABC):
    """Base implementation for platform clients with common functionality."""

    def __init__(self, config: Config) -> None:
        """Initialize platform client."""
        self.config = config
        self._authenticated_username: str | None = None

    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from AI review based on patterns.

        Args:
            file_path: Path of the file to check

        Returns:
            True if file should be excluded, False otherwise
        """
        path = PurePath(file_path)
        for pattern in self.config.exclude_patterns:
            try:
                # Use PurePath.match() for glob patterns with ** support
                if path.match(pattern):
                    return True
                # Also try fnmatch for simple patterns (fallback)
                if fnmatch.fnmatch(file_path, pattern):
                    return True
            except (ValueError, TypeError):
                # If pattern is invalid, try fnmatch as fallback
                if fnmatch.fnmatch(file_path, pattern):
                    return True
        return False

    def _apply_content_limits(
        self, diffs: list[PullRequestDiff]
    ) -> list[PullRequestDiff]:
        """Apply content size limits to diffs."""
        total_chars = 0
        limited_diffs: list[PullRequestDiff] = []

        for diff in diffs:
            # Check if adding this diff exceeds the limit
            diff_chars = len(diff.diff)
            if total_chars + diff_chars > self.config.max_chars:
                # Try to truncate this diff
                remaining_chars = self.config.max_chars - total_chars
                if remaining_chars > 20:  # Only include if we have meaningful content
                    truncated_diff = PullRequestDiff(
                        file_path=diff.file_path,
                        new_file=diff.new_file,
                        renamed_file=diff.renamed_file,
                        deleted_file=diff.deleted_file,
                        diff=diff.diff[:remaining_chars] + "\n... (diff truncated)",
                    )
                    limited_diffs.append(truncated_diff)
                break

            limited_diffs.append(diff)
            total_chars += diff_chars

        return limited_diffs

    @abstractmethod
    async def get_authenticated_username(self) -> str:
        """Get username of authenticated user (bot).

        This is used to identify which comments/reviews were made by this bot
        to prioritize author responses to previous AI reviews.

        Returns:
            Username/login of the authenticated user

        Raises:
            PlatformAPIError: If API call fails
        """
        pass

    @abstractmethod
    async def get_pull_request_data(
        self, project_id: str, pr_number: int
    ) -> PullRequestData:
        """Fetch complete pull/merge request data including diffs."""
        pass

    @abstractmethod
    async def post_review(
        self, project_id: str, pr_number: int, review_content: str
    ) -> PostReviewResponse:
        """Post review as a comment on the pull/merge request."""
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name of the platform."""
        pass

    @abstractmethod
    def format_project_url(self, project_id: str) -> str:
        """Format the project URL for this platform."""
        pass
