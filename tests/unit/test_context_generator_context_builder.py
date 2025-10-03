"""Tests for ContextBuilder."""

from __future__ import annotations

# Import the GitTestMixin
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ai_code_review.models.config import Config
from context_generator.core.context_builder import ContextBuilder
from context_generator.models import ContextResult

sys.path.append(str(Path(__file__).parent))
from test_context_generator_base import GitTestMixin


class TestContextBuilder(GitTestMixin):
    """Test ContextBuilder functionality."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        self._cleanup_git_mocks()

    def test_init(self) -> None:
        """Test ContextBuilder initialization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            builder = ContextBuilder(project_path, config, skip_git_validation=True)

            assert builder.project_path == project_path
            assert builder.config == config
            assert builder.facts_extractor is not None
            assert builder.code_extractor is not None
            assert builder.llm_analyzer is not None
            assert builder.template_engine is not None
            assert builder.section_registry is not None

    @pytest.mark.asyncio
    async def test_generate_context_full(self) -> None:
        """Test full context generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create basic project
            (project_path / "README.md").write_text("# Test Project")
            (project_path / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "1.0.0"
dependencies = ["click"]
""")

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            builder = ContextBuilder(project_path, config, skip_git_validation=True)
            result = await builder.generate_context()

            # Verify result structure
            assert isinstance(result, ContextResult)
            assert result.project_path == project_path
            assert result.project_name == project_path.name
            assert len(result.context_content) > 0
            assert result.ai_provider == "ollama"
            assert result.ai_model == "qwen2.5-coder:7b"

            # Verify content structure
            assert "# Project Context for AI Code Review" in result.context_content
            assert "## Project Overview" in result.context_content
            assert "## Technology Stack" in result.context_content

    @pytest.mark.asyncio
    async def test_generate_context_with_target_sections(self) -> None:
        """Test context generation with specific target sections."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            # Create basic project
            (project_path / "README.md").write_text("# Test Project")

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            builder = ContextBuilder(project_path, config, skip_git_validation=True)

            # Test with specific sections
            target_sections = ["project_overview", "tech_stack"]
            result = await builder.generate_context(target_sections=target_sections)

            assert isinstance(result, ContextResult)
            assert len(result.context_content) > 0

    @pytest.mark.asyncio
    async def test_generate_context_with_output_path(self) -> None:
        """Test context generation with output path for template preservation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)
            output_path = Path(tmp_dir) / "context.md"

            # Create basic project
            (project_path / "README.md").write_text("# Test Project")

            # Create existing context file with manual sections
            output_path.write_text("""
# Project Context for AI Code Review

## Project Overview
Old content

---
<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->
<!-- The sections below will be preserved during updates -->

## Business Logic & Implementation Decisions
Manual content here
""")

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            builder = ContextBuilder(project_path, config, skip_git_validation=True)
            result = await builder.generate_context(output_path=output_path)

            assert isinstance(result, ContextResult)
            # Manual sections should be preserved in template engine
            assert "Manual content here" in result.context_content

    def test_get_generation_summary(self) -> None:
        """Test generation summary."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                ai_model="llama2",
                dry_run=True,
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            builder = ContextBuilder(project_path, config, skip_git_validation=True)
            summary = builder.get_generation_summary()

            assert isinstance(summary, dict)
            assert summary["project_name"] == project_path.name
            assert summary["ai_provider"] == "ollama"
            assert summary["ai_model"] == "llama2"
            assert summary["dry_run"] is True

    @pytest.mark.asyncio
    async def test_section_generation_error_handling(self) -> None:
        """Test error handling in section generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            builder = ContextBuilder(project_path, config, skip_git_validation=True)

            # Mock section to simulate error
            with patch.object(
                builder.section_registry, "get_available_sections"
            ) as mock_sections:
                mock_section = Mock()
                mock_section.name = "test_section"
                mock_section.generate_content = AsyncMock(
                    side_effect=Exception("Test error")
                )
                mock_sections.return_value = [mock_section]

                # Should handle error gracefully
                result = await builder.generate_context()
                assert isinstance(result, ContextResult)
                # Error sections should have placeholder content

    @pytest.mark.asyncio
    async def test_parallel_section_generation_fallback(self) -> None:
        """Test fallback to individual generation when parallel fails."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            builder = ContextBuilder(project_path, config, skip_git_validation=True)

            # Mock asyncio.gather to fail first time
            call_count = 0

            async def mock_gather(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Parallel generation failed")
                return ["Mock content"] * len(args)

            with patch("asyncio.gather", side_effect=mock_gather):
                result = await builder.generate_context()
                assert isinstance(result, ContextResult)
                # Should have fallen back to individual generation

    def test_register_core_sections(self) -> None:
        """Test that core sections are registered properly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_path = Path(tmp_dir)

            config = Config(
                gitlab_token="dummy",
                github_token="dummy",
                ai_provider="ollama",
                dry_run=True,
            )

            # Create fast git repo simulation
            self._create_fast_git_repo(project_path)

            builder = ContextBuilder(project_path, config, skip_git_validation=True)

            # Verify all core sections are registered
            sections = builder.section_registry.sections
            section_names = [section.name for section in sections]

            expected_sections = ["overview", "tech_stack", "structure", "review_focus"]
            for expected in expected_sections:
                assert expected in section_names
