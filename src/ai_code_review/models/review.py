"""Review data models."""

from __future__ import annotations

from pydantic import BaseModel


class ReviewComment(BaseModel):
    """A single review comment on a file."""

    file_path: str
    issue_type: str  # e.g., "Security", "Performance", "Logic"
    description: str
    reasoning: str
    suggestion: str
    code_example: str | None = None
    line_number: int | None = None


class FileReview(BaseModel):
    """Review for a single file."""

    file_path: str
    summary: str
    comments: list[ReviewComment]
    questions: list[str] = []
    additional_notes: list[str] = []


class CodeReview(BaseModel):
    """Complete code review for a merge request."""

    general_feedback: str
    file_reviews: list[FileReview]
    overall_assessment: str
    priority_issues: list[str] = []
    minor_suggestions: list[str] = []


class ReviewSummary(BaseModel):
    """High-level summary of a merge request."""

    title: str
    key_changes: list[str]
    modules_affected: list[str]
    user_impact: str
    technical_impact: str
    risk_level: str  # "Low", "Medium", "High"
    risk_justification: str


class ReviewResult(BaseModel):
    """Complete review result including both review and optional summary."""

    review: CodeReview
    summary: ReviewSummary | None = None

    def to_markdown(self) -> str:
        """Convert review result to markdown format.

        The LLM response already contains the complete structured review
        with summary and detailed sections, so we use it directly.
        """
        return self.review.general_feedback
