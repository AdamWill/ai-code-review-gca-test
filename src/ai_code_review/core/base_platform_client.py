"""Base platform client implementation."""

from __future__ import annotations

import asyncio
import fnmatch
from abc import ABC, abstractmethod
from pathlib import PurePath
from typing import Any

import httpx
import structlog
import unidiff  # type: ignore

from ai_code_review.models.config import Config
from ai_code_review.models.platform import (
    PlatformClientInterface,
    PostReviewResponse,
    PullRequestData,
    PullRequestDiff,
)

logger = structlog.get_logger(__name__)


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
        # max_chars should never be None after Config initialization
        # (set by adaptive validator if not explicitly provided)
        if self.config.max_chars is None:
            raise ValueError(
                "max_chars must be set. This indicates a configuration error."
            )

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

    def _convert_patchset_to_diffs(self, patch_set: Any) -> list[PullRequestDiff]:
        """Convert unidiff PatchSet to our PullRequestDiff format.

        Applies filtering for binary files and excluded patterns,
        and enforces max_files limit.

        Args:
            patch_set: unidiff.PatchSet object with parsed diffs

        Returns:
            List of filtered and converted PullRequestDiff objects
        """
        diffs: list[PullRequestDiff] = []
        binary_skipped = 0
        excluded_by_pattern = 0

        for patched_file in patch_set:
            file_path = patched_file.path

            # Skip binaries (unidiff detects via "Binary files differ")
            if patched_file.is_binary_file:
                binary_skipped += 1
                continue

            # Apply user exclusion patterns
            if self._should_exclude_file(file_path):
                excluded_by_pattern += 1
                continue

            diffs.append(
                PullRequestDiff(
                    file_path=file_path,
                    new_file=patched_file.is_added_file,
                    renamed_file=patched_file.is_rename,
                    deleted_file=patched_file.is_removed_file,
                    diff=str(patched_file),
                )
            )

            if len(diffs) >= self.config.max_files:
                logger.info(
                    "Reached max_files limit",
                    max_files=self.config.max_files,
                )
                break

        logger.info(
            "Complete diff fetched via HTTP",
            total_files=len(patch_set),
            included=len(diffs),
            binary_skipped=binary_skipped,
            excluded_by_pattern=excluded_by_pattern,
        )

        return diffs

    async def _fetch_diff_via_http(
        self,
        diff_url: str,
        headers: dict[str, str],
        ssl_context: Any = True,
    ) -> list[PullRequestDiff] | None:
        """Fetch and parse diff via HTTP .diff URL.

        This method provides a common implementation for fetching complete diffs
        via HTTP, which is more reliable than API endpoints for large files.

        Args:
            diff_url: The URL to fetch the diff from
            headers: HTTP headers (authentication, etc.)
            ssl_context: SSL context for verification (True, False, or ssl.SSLContext)

        Returns:
            List of PullRequestDiff objects if successful, None if fetch fails
        """
        try:
            timeout = httpx.Timeout(self.config.diff_download_timeout)
            async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
                response = await client.get(diff_url, headers=headers)

                if response.status_code == 200:
                    # Parse with unidiff - it handles binary detection automatically
                    # Use to_thread for CPU-bound parsing to avoid blocking event loop
                    patch_set = await asyncio.to_thread(unidiff.PatchSet, response.text)

                    # Convert to our format (shared logic)
                    diffs = self._convert_patchset_to_diffs(patch_set)

                    return self._apply_content_limits(diffs)

        except Exception as e:
            logger.info(
                "HTTP diff fetch failed, using API fallback",
                error=str(e),
            )

        return None

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
