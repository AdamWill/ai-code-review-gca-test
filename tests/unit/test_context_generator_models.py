"""Tests for context generator models."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from context_generator.models import ContextResult


class TestContextResult:
    """Tests for ContextResult model."""

    def test_context_result_creation(self) -> None:
        """Test ContextResult model creation."""
        result = ContextResult(
            project_path=Path("/test/project"),
            project_name="test-project",
            context_content="# Test Context\nThis is test content",
            generation_timestamp="2024-01-01T12:00:00",
            ai_provider="ollama",
            ai_model="qwen2.5-coder:7b",
        )

        assert result.project_path == Path("/test/project")
        assert result.project_name == "test-project"
        assert result.context_content == "# Test Context\nThis is test content"
        assert result.generation_timestamp == "2024-01-01T12:00:00"
        assert result.ai_provider == "ollama"
        assert result.ai_model == "qwen2.5-coder:7b"

    def test_context_result_create_classmethod(self) -> None:
        """Test ContextResult.create class method."""
        # Mock datetime.now() to get predictable timestamp
        with pytest.MonkeyPatch().context() as m:
            fake_datetime = datetime(2024, 1, 15, 10, 30, 45)
            m.setattr(
                "context_generator.models.datetime",
                type("MockDateTime", (), {"now": lambda: fake_datetime}),
            )

            result = ContextResult.create(
                project_path=Path("/example/project"),
                project_name="example-project",
                context_content="# Example Context\nGenerated content here",
                ai_provider="anthropic",
                ai_model="claude-sonnet-4-20250514",
            )

            assert result.project_path == Path("/example/project")
            assert result.project_name == "example-project"
            assert result.context_content == "# Example Context\nGenerated content here"
            assert result.ai_provider == "anthropic"
            assert result.ai_model == "claude-sonnet-4-20250514"
            assert result.generation_timestamp == "2024-01-15T10:30:45"

    def test_context_result_create_with_current_timestamp(self) -> None:
        """Test ContextResult.create generates current timestamp."""
        before_creation = datetime.now()

        result = ContextResult.create(
            project_path=Path("/current/project"),
            project_name="current-project",
            context_content="Content with current timestamp",
            ai_provider="gemini",
            ai_model="gemini-2.5-pro",
        )

        after_creation = datetime.now()

        # Parse the timestamp from the result
        result_timestamp = datetime.fromisoformat(result.generation_timestamp)

        # Verify timestamp is between before and after creation
        assert before_creation <= result_timestamp <= after_creation

    def test_context_result_serialization(self) -> None:
        """Test ContextResult can be serialized to dict."""
        result = ContextResult(
            project_path=Path("/serialize/test"),
            project_name="serialize-test",
            context_content="Serialization test content",
            generation_timestamp="2024-02-01T14:20:30",
            ai_provider="ollama",
            ai_model="llama3.1:8b",
        )

        data = result.model_dump()

        assert isinstance(data, dict)
        assert str(data["project_path"]) == "/serialize/test"
        assert data["project_name"] == "serialize-test"
        assert data["context_content"] == "Serialization test content"
        assert data["generation_timestamp"] == "2024-02-01T14:20:30"
        assert data["ai_provider"] == "ollama"
        assert data["ai_model"] == "llama3.1:8b"

    def test_context_result_from_dict(self) -> None:
        """Test ContextResult can be created from dict."""
        data = {
            "project_path": "/from/dict/test",
            "project_name": "from-dict-test",
            "context_content": "Content from dict",
            "generation_timestamp": "2024-03-01T16:45:12",
            "ai_provider": "anthropic",
            "ai_model": "claude-3-haiku-20240307",
        }

        result = ContextResult(**data)

        assert result.project_path == Path("/from/dict/test")
        assert result.project_name == "from-dict-test"
        assert result.context_content == "Content from dict"
        assert result.generation_timestamp == "2024-03-01T16:45:12"
        assert result.ai_provider == "anthropic"
        assert result.ai_model == "claude-3-haiku-20240307"

    def test_context_result_validation(self) -> None:
        """Test ContextResult validates required fields."""
        with pytest.raises(ValueError):
            ContextResult()  # Missing required fields

    def test_context_result_path_conversion(self) -> None:
        """Test ContextResult converts string paths to Path objects."""
        result = ContextResult(
            project_path="/string/path/to/project",  # String path
            project_name="path-conversion-test",
            context_content="Path conversion test",
            generation_timestamp="2024-04-01T08:15:00",
            ai_provider="gemini",
            ai_model="gemini-2.0-flash-exp",
        )

        assert isinstance(result.project_path, Path)
        assert result.project_path == Path("/string/path/to/project")

    def test_context_result_empty_content_allowed(self) -> None:
        """Test ContextResult allows empty context content."""
        result = ContextResult(
            project_path=Path("/empty/content/test"),
            project_name="empty-content-test",
            context_content="",  # Empty content should be allowed
            generation_timestamp="2024-05-01T12:30:45",
            ai_provider="ollama",
            ai_model="codellama:13b",
        )

        assert result.context_content == ""
        assert len(result.context_content) == 0

    def test_context_result_long_content(self) -> None:
        """Test ContextResult handles long context content."""
        long_content = "# Long Content Test\n" + "This is a very long line. " * 1000

        result = ContextResult(
            project_path=Path("/long/content/test"),
            project_name="long-content-test",
            context_content=long_content,
            generation_timestamp="2024-06-01T20:45:30",
            ai_provider="anthropic",
            ai_model="claude-sonnet-4-20250514",
        )

        assert len(result.context_content) > 10000
        assert "Long Content Test" in result.context_content
        assert result.context_content.count("This is a very long line.") == 1000
