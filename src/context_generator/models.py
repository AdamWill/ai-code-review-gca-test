"""Data models for context generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class ContextResult(BaseModel):
    """Result of context generation."""

    project_path: Path
    project_name: str
    context_content: str
    generation_timestamp: str
    ai_provider: str
    ai_model: str

    @classmethod
    def create(
        cls,
        project_path: Path,
        project_name: str,
        context_content: str,
        ai_provider: str,
        ai_model: str,
    ) -> ContextResult:
        """Create a new context result."""
        return cls(
            project_path=project_path,
            project_name=project_name,
            context_content=context_content,
            generation_timestamp=datetime.now().isoformat(),
            ai_provider=ai_provider,
            ai_model=ai_model,
        )
