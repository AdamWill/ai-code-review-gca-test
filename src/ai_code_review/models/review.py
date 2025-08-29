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
        """Convert review result to markdown format."""
        sections = []

        # Add MR summary FIRST if available (executive overview comes first)
        if self.summary:
            sections.append("## 📋 MR Executive Summary\n")
            sections.append(f"**Headline:** {self.summary.title}\n")

            if self.summary.key_changes:
                sections.append("**Key Changes:**")
                for change in self.summary.key_changes:
                    sections.append(f"- {change}")
                sections.append("")

            sections.append(
                f"**Impact:** {', '.join(self.summary.modules_affected) if self.summary.modules_affected else 'Multiple components'}"
            )
            if self.summary.user_impact != "To be determined":
                sections.append(f" | User: {self.summary.user_impact}")
            if (
                self.summary.technical_impact
                and self.summary.technical_impact != "To be determined"
            ):
                sections.append(f" | Technical: {self.summary.technical_impact}")
            sections.append("")

            sections.append(
                f"**Risk Level:** {self.summary.risk_level} - {self.summary.risk_justification}"
            )
            sections.append("\n---\n")

        # Add AI-generated detailed review SECOND
        sections.append(self.review.general_feedback)

        return "\n".join(sections)
