"""Common platform-agnostic data models for code hosting platforms."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class PullRequestDiff(BaseModel):
    """Represents a diff for a pull/merge request (platform-agnostic)."""

    file_path: str
    new_file: bool = False
    renamed_file: bool = False
    deleted_file: bool = False
    diff: str


class PullRequestCommit(BaseModel):
    """Represents a commit in the pull/merge request (platform-agnostic)."""

    id: str
    title: str
    message: str
    author_name: str
    author_email: str
    committed_date: str
    short_id: str


class PullRequestInfo(BaseModel):
    """Basic pull/merge request information (platform-agnostic)."""

    id: int
    number: int  # GitHub: PR number, GitLab: MR IID
    title: str
    description: str | None = None
    source_branch: str
    target_branch: str
    author: str
    state: str
    web_url: str
    draft: bool = False  # True if PR/MR is in draft/WIP mode


class PullRequestData(BaseModel):
    """Complete PR/MR data with diffs and commits (platform-agnostic)."""

    info: PullRequestInfo
    diffs: list[PullRequestDiff]
    commits: list[PullRequestCommit]

    @property
    def total_chars(self) -> int:
        """Calculate total characters in all diffs."""
        return sum(len(diff.diff) for diff in self.diffs)

    @property
    def file_count(self) -> int:
        """Get number of modified files."""
        return len(self.diffs)

    @property
    def commit_count(self) -> int:
        """Get number of commits."""
        return len(self.commits)


class PostReviewResponse(BaseModel):
    """Response from posting a review comment (platform-agnostic)."""

    id: str
    url: str
    created_at: str
    author: str
    content_preview: str | None = None


class PlatformClientInterface(ABC):
    """Abstract interface for platform clients (GitLab, GitHub, etc.)."""

    @abstractmethod
    async def get_pull_request_data(
        self, project_id: str, pr_number: int
    ) -> PullRequestData:
        """Fetch complete pull/merge request data including diffs.

        Args:
            project_id: Platform-specific project identifier
            pr_number: Pull/merge request number

        Returns:
            Complete pull request data with diffs

        Raises:
            PlatformAPIError: If API call fails
        """
        pass

    @abstractmethod
    async def post_review(
        self, project_id: str, pr_number: int, review_content: str
    ) -> PostReviewResponse:
        """Post review as a comment on the pull/merge request.

        Args:
            project_id: Platform-specific project identifier
            pr_number: Pull/merge request number
            review_content: The markdown content of the review to post

        Returns:
            Response containing comment information

        Raises:
            PlatformAPIError: If posting fails
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name of the platform (e.g., 'gitlab', 'github')."""
        pass

    @abstractmethod
    def format_project_url(self, project_id: str) -> str:
        """Format the project URL for this platform."""
        pass
