"""Tests for prompt templates and chains."""

from __future__ import annotations

from unittest.mock import MagicMock

from ai_code_review.utils.prompts import (
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
        prompt = create_system_prompt("test-model", "test-provider")

        assert "expert senior software engineer" in prompt
        assert "test-model" in prompt
        assert "test-provider" in prompt

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
