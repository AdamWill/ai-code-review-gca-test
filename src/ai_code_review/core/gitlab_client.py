"""GitLab API client for fetching merge request data."""

from __future__ import annotations

import gitlab
from gitlab.v4.objects import Project, ProjectMergeRequest

from ai_code_review.models.config import Config
from ai_code_review.models.gitlab import (
    MergeRequestCommit,
    MergeRequestData,
    MergeRequestDiff,
    MergeRequestInfo,
)
from ai_code_review.utils.exceptions import GitLabAPIError


class GitLabClient:
    """Client for GitLab API operations."""

    def __init__(self, config: Config) -> None:
        """Initialize GitLab client."""
        self.config = config
        self._gitlab_client: gitlab.Gitlab | None = None

    @property
    def gitlab_client(self) -> gitlab.Gitlab:
        """Get or create GitLab client instance."""
        if self._gitlab_client is None:
            self._gitlab_client = gitlab.Gitlab(
                url=self.config.gitlab_url, private_token=self.config.gitlab_token
            )
        return self._gitlab_client

    async def get_merge_request_data(
        self, project_id: str | int, mr_iid: int
    ) -> MergeRequestData:
        """Fetch complete merge request data including diffs.

        Args:
            project_id: GitLab project ID or path (e.g., 'group/project')
            mr_iid: Merge request IID

        Returns:
            Complete merge request data with diffs

        Raises:
            GitLabAPIError: If API call fails
        """
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_mr_data(project_id, mr_iid)

        try:
            # Get project
            project: Project = self.gitlab_client.projects.get(project_id)

            # Get merge request
            merge_request: ProjectMergeRequest = project.mergerequests.get(mr_iid)

            # Create MR info
            mr_info = MergeRequestInfo(
                id=merge_request.id,
                iid=merge_request.iid,
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

            return MergeRequestData(info=mr_info, diffs=diffs, commits=commits)

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to fetch MR data: {e}", getattr(e, "response_code", None)
            ) from e
        except Exception as e:
            raise GitLabAPIError(f"Unexpected error: {e}") from e

    async def _fetch_merge_request_diffs(
        self, merge_request: ProjectMergeRequest
    ) -> list[MergeRequestDiff]:
        """Fetch diffs for a merge request."""
        diffs: list[MergeRequestDiff] = []

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

            for change in changes_data.get("changes", []):
                # Skip binary files or files without diffs
                if not change.get("diff"):
                    continue

                # Create diff object
                diff = MergeRequestDiff(
                    file_path=change["new_path"] or change["old_path"],
                    new_file=change["new_file"],
                    renamed_file=change["renamed_file"],
                    deleted_file=change["deleted_file"],
                    diff=change["diff"],
                )

                diffs.append(diff)

                # Check limits
                if len(diffs) >= self.config.max_files:
                    break

            return self._apply_content_limits(diffs)

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to fetch diffs: {e}", getattr(e, "response_code", None)
            ) from e

    async def _fetch_merge_request_commits(
        self, merge_request: ProjectMergeRequest
    ) -> list[MergeRequestCommit]:
        """Fetch commits for a merge request."""
        commits: list[MergeRequestCommit] = []

        try:
            # Get commits from the MR
            mr_commits = merge_request.commits()

            for commit_data in mr_commits:
                commit = MergeRequestCommit(
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

    def _apply_content_limits(
        self, diffs: list[MergeRequestDiff]
    ) -> list[MergeRequestDiff]:
        """Apply content size limits to diffs."""
        total_chars = 0
        limited_diffs: list[MergeRequestDiff] = []

        for diff in diffs:
            # Check if adding this diff exceeds the limit
            diff_chars = len(diff.diff)
            if total_chars + diff_chars > self.config.max_chars:
                # Try to truncate this diff
                remaining_chars = self.config.max_chars - total_chars
                if remaining_chars > 20:  # Only include if we have meaningful content
                    truncated_diff = MergeRequestDiff(
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

    def _create_mock_mr_data(
        self, project_id: str | int, mr_iid: int
    ) -> MergeRequestData:
        """Create mock merge request data for dry run mode."""
        mock_info = MergeRequestInfo(
            id=12345,
            iid=mr_iid,
            title=f"Mock MR {mr_iid} for project {project_id}",
            description="Mock merge request for testing",
            source_branch="feature/mock-branch",
            target_branch="main",
            author="mock_user",
            state="opened",
            web_url=f"{self.config.gitlab_url}/mock/project/-/merge_requests/{mr_iid}",
        )

        mock_diffs = [
            MergeRequestDiff(
                file_path="src/mock_file.py",
                new_file=False,
                diff="@@ -1,3 +1,3 @@\n def mock_function():\n-    return 'old'\n+    return 'new'",
            )
        ]

        mock_commits = [
            MergeRequestCommit(
                id="abc123456789",
                title="Add world greeting feature",
                message="Add world greeting feature\n\nImplements the requested greeting functionality to improve user experience.",
                author_name="Mock Author",
                author_email="author@example.com",
                committed_date="2024-01-01T12:00:00Z",
                short_id="abc1234",
            )
        ]

        return MergeRequestData(info=mock_info, diffs=mock_diffs, commits=mock_commits)

    async def post_review(
        self, project_id: str | int, mr_iid: int, review_content: str
    ) -> dict[str, str]:
        """Post review as a note/comment on the merge request.

        Args:
            project_id: GitLab project ID or path (e.g., 'group/project')
            mr_iid: Merge request IID
            review_content: The markdown content of the review to post

        Returns:
            Dictionary containing note information (id, url, etc.)

        Raises:
            GitLabAPIError: If posting fails
        """
        if self.config.dry_run:
            # Return mock data for dry run
            return self._create_mock_note_data(project_id, mr_iid, review_content)

        try:
            # Get project
            project: Project = self.gitlab_client.projects.get(project_id)

            # Get merge request
            merge_request: ProjectMergeRequest = project.mergerequests.get(mr_iid)

            # Create the note on the MR
            note = merge_request.notes.create({"body": review_content})

            # Return note information
            return {
                "id": str(note.id),
                "url": f"{self.config.gitlab_url}/-/merge_requests/{mr_iid}#note_{note.id}",
                "created_at": note.created_at,
                "author": note.author["name"]
                if "author" in note.__dict__
                else "AI Code Review",
            }

        except gitlab.GitlabError as e:
            raise GitLabAPIError(
                f"Failed to post review to GitLab: {e}",
                getattr(e, "response_code", None),
            ) from e
        except Exception as e:
            raise GitLabAPIError(f"Unexpected error posting review: {e}") from e

    def _create_mock_note_data(
        self, project_id: str | int, mr_iid: int, review_content: str
    ) -> dict[str, str]:
        """Create mock note data for dry run mode."""
        return {
            "id": "mock_note_123",
            "url": f"{self.config.gitlab_url}/mock/project/-/merge_requests/{mr_iid}#note_mock_123",
            "created_at": "2024-01-01T12:00:00Z",
            "author": "AI Code Review (DRY RUN)",
            "content_preview": review_content[:100] + "..."
            if len(review_content) > 100
            else review_content,
        }
