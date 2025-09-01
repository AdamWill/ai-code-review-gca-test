"""GitLab API client for fetching merge request data."""

from __future__ import annotations

import gitlab
import structlog
from gitlab.v4.objects import Project, ProjectMergeRequest

from ai_code_review.core.base_platform_client import BasePlatformClient
from ai_code_review.models.config import Config
from ai_code_review.models.platform import (
    PostReviewResponse,
    PullRequestCommit,
    PullRequestData,
    PullRequestDiff,
    PullRequestInfo,
)
from ai_code_review.utils.platform_exceptions import GitLabAPIError


class GitLabClient(BasePlatformClient):
    """Client for GitLab API operations."""

    def __init__(self, config: Config) -> None:
        """Initialize GitLab client."""
        super().__init__(config)
        self._gitlab_client: gitlab.Gitlab | None = None

    @property
    def gitlab_client(self) -> gitlab.Gitlab:
        """Get or create GitLab client instance."""
        if self._gitlab_client is None:
            # Configure SSL verification
            ssl_verify: bool | str = self.config.ssl_verify
            if self.config.ssl_cert_path is not None:
                # Use custom certificate file
                ssl_verify = self.config.ssl_cert_path

            self._gitlab_client = gitlab.Gitlab(
                url=self.config.gitlab_url,
                private_token=self.config.get_platform_token(),
                ssl_verify=ssl_verify,
            )
        return self._gitlab_client

    async def get_pull_request_data(
        self, project_id: str, pr_number: int
    ) -> PullRequestData:
        """Fetch complete merge request data including diffs.

        Args:
            project_id: GitLab project ID or path (e.g., 'group/project')
            pr_number: Merge request IID

        Returns:
            Complete merge request data with diffs

        Raises:
            GitLabAPIError: If API call fails
        """
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_pr_data(project_id, pr_number)

        try:
            # Get project
            project: Project = self.gitlab_client.projects.get(project_id)

            # Get merge request
            merge_request: ProjectMergeRequest = project.mergerequests.get(pr_number)

            # Create PR info (mapping GitLab MR to platform-agnostic model)
            pr_info = PullRequestInfo(
                id=merge_request.id,
                number=merge_request.iid,  # GitLab uses iid as the "number"
                title=merge_request.title,
                description=merge_request.description,
                source_branch=merge_request.source_branch,
                target_branch=merge_request.target_branch,
                author=merge_request.author["name"],
                state=merge_request.state,
                web_url=merge_request.web_url,
            )

            # Get diffs and commits
            diffs = await self._fetch_merge_request_diffs(merge_request)
            commits = await self._fetch_merge_request_commits(merge_request)

            return PullRequestData(info=pr_info, diffs=diffs, commits=commits)

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to fetch MR data: {e}", getattr(e, "response_code", None)
            ) from e
        except Exception as e:
            raise GitLabAPIError(f"Unexpected error: {e}") from e

    async def _fetch_merge_request_diffs(
        self, merge_request: ProjectMergeRequest
    ) -> list[PullRequestDiff]:
        """Fetch diffs for a merge request."""
        diffs: list[PullRequestDiff] = []
        excluded_files: list[str] = []
        excluded_chars = 0

        try:
            # Get changes from the MR
            changes_response = merge_request.changes()

            # Handle both dict and Response types
            if hasattr(changes_response, "get"):
                changes_data = changes_response
            else:
                # If it's a Response object, convert to dict
                changes_data = (
                    changes_response.json() if hasattr(changes_response, "json") else {}
                )

            # Track files skipped due to missing diff content (common for large lockfiles)
            skipped_no_diff = []

            for change in changes_data.get("changes", []):
                file_path = change["new_path"] or change["old_path"]
                diff_content = change.get("diff", "")

                # Skip binary files or files without diffs
                if not diff_content:
                    skipped_no_diff.append(file_path)
                    continue

                # Check if file should be excluded from AI review
                if self._should_exclude_file(file_path):
                    excluded_files.append(file_path)
                    excluded_chars += len(diff_content)
                    continue  # Skip excluded files

                # Create diff object
                diff = PullRequestDiff(
                    file_path=file_path,
                    new_file=change["new_file"],
                    renamed_file=change["renamed_file"],
                    deleted_file=change["deleted_file"],
                    diff=change["diff"],
                )

                diffs.append(diff)

                # Check limits
                if len(diffs) >= self.config.max_files:
                    break

            # Log filtering and skipping statistics
            logger = structlog.get_logger()

            if excluded_files:
                logger.info(
                    "Files excluded from AI review",
                    excluded_files=len(excluded_files),
                    excluded_chars=excluded_chars,
                    included_files=len(diffs),
                    examples=excluded_files[:3],  # Show first 3 examples
                )

            if skipped_no_diff:
                logger.info(
                    "Files skipped - no diff content from GitLab API",
                    skipped_files=len(skipped_no_diff),
                    reason="GitLab omits diff content for large files (e.g., lockfiles)",
                    examples=skipped_no_diff[:3],  # Show first 3 examples
                )

            return self._apply_content_limits(diffs)

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to fetch diffs: {e}", getattr(e, "response_code", None)
            ) from e

    async def _fetch_merge_request_commits(
        self, merge_request: ProjectMergeRequest
    ) -> list[PullRequestCommit]:
        """Fetch commits for a merge request."""
        commits: list[PullRequestCommit] = []

        try:
            # Get commits from the MR
            mr_commits = merge_request.commits()

            for commit_data in mr_commits:
                commit = PullRequestCommit(
                    id=commit_data.id,
                    title=commit_data.title,
                    message=commit_data.message,
                    author_name=commit_data.author_name,
                    author_email=commit_data.author_email,
                    committed_date=commit_data.committed_date,
                    short_id=commit_data.short_id,
                )
                commits.append(commit)

            return commits

        except Exception as e:
            raise GitLabAPIError(
                f"Failed to fetch commits: {e}", getattr(e, "response_code", None)
            ) from e

    def _create_mock_pr_data(self, project_id: str, pr_number: int) -> PullRequestData:
        """Create mock merge request data for dry run mode."""
        mock_info = PullRequestInfo(
            id=12345,
            number=pr_number,
            title=f"Mock MR {pr_number} for project {project_id}",
            description="Mock merge request for testing",
            source_branch="feature/mock-branch",
            target_branch="main",
            author="mock_user",
            state="opened",
            web_url=f"{self.config.gitlab_url}/mock/project/-/merge_requests/{pr_number}",
        )

        mock_diffs = [
            PullRequestDiff(
                file_path="src/mock_file.py",
                new_file=False,
                diff="@@ -1,3 +1,3 @@\n def mock_function():\n-    return 'old'\n+    return 'new'",
            )
        ]

        mock_commits = [
            PullRequestCommit(
                id="abc123456789",
                title="Add world greeting feature",
                message="Add world greeting feature\n\nImplements the requested greeting functionality to improve user experience.",
                author_name="Mock Author",
                author_email="author@example.com",
                committed_date="2024-01-01T12:00:00Z",
                short_id="abc1234",
            )
        ]

        return PullRequestData(info=mock_info, diffs=mock_diffs, commits=mock_commits)

    async def post_review(
        self, project_id: str, pr_number: int, review_content: str
    ) -> PostReviewResponse:
        """Post review as a note/comment on the merge request.

        Args:
            project_id: GitLab project ID or path (e.g., 'group/project')
            pr_number: Merge request IID
            review_content: The markdown content of the review to post

        Returns:
            Response containing note information

        Raises:
            GitLabAPIError: If posting fails
        """
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_note_data(project_id, pr_number, review_content)

        try:
            # Get project
            project: Project = self.gitlab_client.projects.get(project_id)

            # Get merge request
            merge_request: ProjectMergeRequest = project.mergerequests.get(pr_number)

            # Create the note on the MR
            note = merge_request.notes.create({"body": review_content})

            # Return note information
            return PostReviewResponse(
                id=str(note.id),
                url=f"{self.config.gitlab_url}/-/merge_requests/{pr_number}#note_{note.id}",
                created_at=note.created_at,
                author=note.author["name"]
                if "author" in note.__dict__
                else "AI Code Review",
            )

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to post review to GitLab: {e}",
                getattr(e, "response_code", None),
            ) from e
        except Exception as e:
            raise GitLabAPIError(f"Unexpected error posting review: {e}") from e

    def _create_mock_note_data(
        self, project_id: str, pr_number: int, review_content: str
    ) -> PostReviewResponse:
        """Create mock note data for dry run mode."""
        return PostReviewResponse(
            id="mock_note_123",
            url=f"{self.config.gitlab_url}/mock/project/-/merge_requests/{pr_number}#note_mock_123",
            created_at="2024-01-01T12:00:00Z",
            author="AI Code Review (DRY RUN)",
            content_preview=review_content[:100] + "..."
            if len(review_content) > 100
            else review_content,
        )

    def get_platform_name(self) -> str:
        """Get the name of the platform."""
        return "gitlab"

    def format_project_url(self, project_id: str) -> str:
        """Format the project URL for GitLab."""
        return f"{self.config.gitlab_url}/{project_id}"
