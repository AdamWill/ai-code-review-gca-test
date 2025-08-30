"""Tests for prompt templates and chains."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from ai_code_review.utils.prompts import (
    _create_language_hint_section,
    _create_project_context_section,
    _extract_diff_content,
    _get_system_prompt,
    create_review_chain,
    create_review_prompt,
    create_system_prompt,
)


class TestPrompts:
    """Test prompt templates."""

    def test_create_system_prompt(self) -> None:
        """Test system prompt creation."""
        prompt = create_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "expert senior software engineer" in prompt.lower()
        assert "focus only on the changes" in prompt.lower()

    def test_create_review_prompt(self) -> None:
        """Test unified review prompt template."""
        prompt = create_review_prompt()

        # Variables are sorted alphabetically by LangChain
        expected_vars = sorted(
            [
                "system_prompt",
                "language_hint_section",
                "project_context_section",
                "diff_content",
            ]
        )
        assert sorted(prompt.input_variables) == expected_vars

        # Verify that the template contains both summary and review sections
        template_str = str(prompt)
        assert "## AI Code Review" in template_str
        assert "### 📋 MR Summary" in template_str
        assert "### Detailed Code Review" in template_str
        assert "#### 📂 File Reviews" in template_str
        # Should NOT contain the "Part 1" and "Part 2" titles
        assert "Part 1:" not in template_str
        assert "Part 2:" not in template_str

    def test_review_chain_creation(self) -> None:
        """Test review chain creation."""
        mock_llm = MagicMock()
        mock_llm.return_value = "Mock unified response with summary and review"

        chain = create_review_chain(mock_llm)

        # Test that chain can be created without errors
        assert chain is not None

    def test_extract_diff_content(self) -> None:
        """Test diff content extraction."""
        input_data = {"diff": "- old line\n+ new line"}
        result = _extract_diff_content(input_data)
        assert result == "- old line\n+ new line"

    def test_create_language_hint_section_with_language(self) -> None:
        """Test language hint section creation with language."""
        input_data = {"language": "Python"}
        result = _create_language_hint_section(input_data)
        assert result == "**Primary Language:** Python"

    def test_create_language_hint_section_without_language(self) -> None:
        """Test language hint section creation without language."""
        input_data: dict[str, Any] = {}
        result = _create_language_hint_section(input_data)
        assert result == ""

    def test_create_project_context_section_with_context(self) -> None:
        """Test project context section creation with context."""
        input_data = {"context": "This is a web API project"}
        result = _create_project_context_section(input_data)
        assert result == "## Project Context\nThis is a web API project"

    def test_create_project_context_section_without_context(self) -> None:
        """Test project context section creation without context."""
        input_data: dict[str, Any] = {}
        result = _create_project_context_section(input_data)
        assert result == ""

    def test_create_project_context_section_with_empty_context(self) -> None:
        """Test project context section creation with empty/whitespace context."""
        input_data = {"context": "   "}
        result = _create_project_context_section(input_data)
        assert result == ""

    def test_get_system_prompt(self) -> None:
        """Test system prompt getter function."""
        input_data = {"some": "data"}  # Input is ignored
        result = _get_system_prompt(input_data)
        expected = create_system_prompt()
        assert result == expected
