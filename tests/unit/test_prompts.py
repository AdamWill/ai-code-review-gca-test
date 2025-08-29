"""Tests for prompt templates and chains."""

from __future__ import annotations

from unittest.mock import MagicMock

from ai_code_review.utils.prompts import (
    _create_language_hint_section,
    _create_project_context_section,
    _extract_diff_content,
    _get_system_prompt,
    create_review_chain,
    create_review_prompt,
    create_summary_chain,
    create_summary_prompt,
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
        assert "review only the changes" in prompt.lower()

    def test_create_review_prompt(self) -> None:
        """Test code review prompt template."""
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

    def test_create_summary_prompt(self) -> None:
        """Test MR summary prompt template."""
        prompt = create_summary_prompt()

        # Variables are sorted alphabetically by LangChain
        expected_vars = sorted(
            ["system_prompt", "project_context_section", "diff_content"]
        )
        assert sorted(prompt.input_variables) == expected_vars

    def test_review_chain_creation(self) -> None:
        """Test code review chain creation."""
        mock_llm = MagicMock()
        mock_llm.return_value = "Mock review response"

        chain = create_review_chain(mock_llm)

        # Test that chain can be created without errors
        assert chain is not None

    def test_summary_chain_creation(self) -> None:
        """Test summary chain creation."""
        mock_llm = MagicMock()
        mock_llm.return_value = "Mock summary response"

        chain = create_summary_chain(mock_llm)

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
        input_data = {}
        result = _create_language_hint_section(input_data)
        assert result == ""

    def test_create_project_context_section_with_context(self) -> None:
        """Test project context section creation with context."""
        input_data = {"context": "This is a web API project"}
        result = _create_project_context_section(input_data)
        assert result == "## Project Context\nThis is a web API project"

    def test_create_project_context_section_without_context(self) -> None:
        """Test project context section creation without context."""
        input_data = {}
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
