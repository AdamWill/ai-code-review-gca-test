"""GitLab data models."""

from __future__ import annotations

from pydantic import BaseModel


class MergeRequestDiff(BaseModel):
    """Represents a diff for a merge request."""

    file_path: str
    new_file: bool = False
    renamed_file: bool = False
    deleted_file: bool = False
    diff: str


class MergeRequestInfo(BaseModel):
    """Basic merge request information."""

    id: int
    iid: int
    title: str
    description: str | None = None
    source_branch: str
    target_branch: str
    author: str
    state: str
    web_url: str


class MergeRequestData(BaseModel):
    """Complete MR data with diffs."""

    info: MergeRequestInfo
    diffs: list[MergeRequestDiff]

    @property
    def total_chars(self) -> int:
        """Calculate total characters in all diffs."""
        return sum(len(diff.diff) for diff in self.diffs)

    @property
    def file_count(self) -> int:
        """Get number of modified files."""
        return len(self.diffs)
