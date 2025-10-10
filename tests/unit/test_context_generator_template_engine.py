"""Tests for TemplateEngine functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from context_generator.templates.template_engine import TemplateEngine


class TestTemplateEngine:
    """Tests for TemplateEngine functionality."""

    # ===== Basic Tests =====

    def test_init(self) -> None:
        """Test TemplateEngine initialization."""
        engine = TemplateEngine()
        assert engine.template_path is not None
        assert engine.template_path.name == "context_template.md"

    def test_load_template(self) -> None:
        """Test _load_template method."""
        engine = TemplateEngine()
        template = engine._load_template()

        assert isinstance(template, str)
        assert len(template) > 0
        # Should contain section placeholders
        assert "{{" in template
        assert "}}" in template

    def test_load_template_file_not_found(self) -> None:
        """Test _load_template when template file doesn't exist."""
        engine = TemplateEngine()

        with patch(
            "pathlib.Path.read_text",
            side_effect=FileNotFoundError("Template not found"),
        ):
            template = engine._load_template()
            # Should return default template
            assert "Project Context for AI Code Review" in template

    def test_load_template_permission_error(self) -> None:
        """Test _load_template when permission error occurs."""
        engine = TemplateEngine()

        with patch(
            "pathlib.Path.read_text",
            side_effect=PermissionError("Permission denied"),
        ):
            template = engine._load_template()
            # Should return default template
            assert "Project Context for AI Code Review" in template

    def test_load_template_unicode_error(self) -> None:
        """Test _load_template when unicode decode error occurs."""
        engine = TemplateEngine()

        with patch(
            "pathlib.Path.read_text",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte"),
        ):
            template = engine._load_template()
            # Should return default template
            assert "Project Context for AI Code Review" in template

    # ===== Metadata Tests =====

    def test_add_metadata(self) -> None:
        """Test _add_metadata method."""
        engine = TemplateEngine()

        content = "# Project Context\n\nSome content"
        facts = {
            "project_info": {
                "name": "test-project",
                "type": "python",
            },
            "dependencies": {
                "runtime": ["fastapi", "pydantic"],
            },
        }

        result = engine._add_metadata(content, facts)

        # Should preserve original content
        assert "# Project Context" in result
        assert "Some content" in result
        # _add_metadata only replaces {{project_name}} placeholder, doesn't add metadata
        assert (
            result == content
        )  # Content should be unchanged since no {{project_name}} placeholder

    def test_add_metadata_with_project_name(self) -> None:
        """Test _add_metadata with project name."""
        engine = TemplateEngine()

        content = "# Test Content for {{project_name}}"
        facts = {
            "project_info": {"name": "my-awesome-project", "type": "web_api"},
        }

        result = engine._add_metadata(content, facts)

        assert "my-awesome-project" in result
        assert "{{project_name}}" not in result

    def test_add_metadata_no_project_info(self) -> None:
        """Test _add_metadata with no project info."""
        engine = TemplateEngine()

        content = "# Test Content with {{project_name}}"
        facts = {}

        result = engine._add_metadata(content, facts)

        # Should replace {{project_name}} with "Unknown Project" when no project info
        assert "Unknown Project" in result
        assert "{{project_name}}" not in result

    # ===== Section Application Tests =====

    def test_apply_sections(self) -> None:
        """Test _apply_sections method."""
        engine = TemplateEngine()

        template = """# Project Context

{{project_overview}}

## Tech Stack
{{tech_stack}}

## Code Structure
{{code_structure}}

## Review Focus
{{review_focus}}

## Library Documentation
{{context7_analysis}}
"""

        section_content = {
            "project_overview": "This is a Python web API project",
            "tech_stack": "FastAPI, Pydantic, PostgreSQL",
            "code_structure": "Standard Python package structure",
            "review_focus": "Focus on API design and validation",
            "context7_analysis": "FastAPI best practices documentation",
        }

        result = engine._apply_sections(template, section_content)

        # Should replace all placeholders
        assert "This is a Python web API project" in result
        assert "FastAPI, Pydantic, PostgreSQL" in result
        assert "Standard Python package structure" in result
        assert "Focus on API design and validation" in result
        assert "FastAPI best practices documentation" in result
        # Should not contain placeholders
        assert "{{project_overview}}" not in result
        assert "{{tech_stack}}" not in result

    def test_apply_sections_missing_content(self) -> None:
        """Test _apply_sections with missing section content."""
        engine = TemplateEngine()

        template = "{{project_overview}}\n{{tech_stack}}"
        section_content = {"project_overview": "Available content"}

        result = engine._apply_sections(template, section_content)

        assert "Available content" in result
        assert "*Tech stack not available*" in result  # Default for missing tech_stack

    # ===== Manual Sections Tests =====

    def test_extract_existing_sections_file_not_exists(self) -> None:
        """Test _extract_existing_sections when file doesn't exist."""
        engine = TemplateEngine()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "nonexistent.md"

            sections = engine._extract_existing_sections(output_path)

            assert sections == {}

    def test_extract_existing_sections_read_error(self) -> None:
        """Test _extract_existing_sections when read error occurs."""
        engine = TemplateEngine()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.md"
            output_path.write_text("# Test")

            with patch(
                "pathlib.Path.read_text",
                side_effect=PermissionError("Permission denied"),
            ):
                sections = engine._extract_existing_sections(output_path)

                assert sections == {}

    def test_extract_manual_sections_no_marker(self) -> None:
        """Test _extract_manual_sections when no marker is found."""
        engine = TemplateEngine()

        content = """# Project Context

Some content without manual sections marker.
"""

        manual_sections = engine._extract_manual_sections(content)

        assert manual_sections == ""

    def test_extract_manual_sections_read_error(self) -> None:
        """Test _extract_manual_sections when content is None."""
        engine = TemplateEngine()

        manual_sections = engine._extract_manual_sections(None)

        assert manual_sections == ""

    def test_merge_manual_sections_with_content(self) -> None:
        """Test _merge_manual_sections with manual content."""
        engine = TemplateEngine()

        rendered = "# Project Context\nGenerated content"
        manual_content = "# Manual Section\nManual content"

        result = engine._merge_manual_sections(rendered, manual_content)

        assert "Generated content" in result
        assert "Manual content" in result

    def test_merge_manual_sections_empty_manual(self) -> None:
        """Test _merge_manual_sections with empty manual content."""
        engine = TemplateEngine()

        rendered = "# Project Context\nGenerated content"
        manual_content = ""

        result = engine._merge_manual_sections(rendered, manual_content)
        # Should contain the original content (might have extra newlines)
        assert "Generated content" in result

    # ===== Fallback Generation Tests =====

    def test_generate_fallback_context_with_content(self) -> None:
        """Test _generate_fallback_context with content."""
        engine = TemplateEngine()

        section_content = {
            "project_overview": "Test project overview",
            "tech_stack": "Python, FastAPI",
        }

        result = engine._generate_fallback_context(section_content)

        assert "Test project overview" in result
        assert "Python, FastAPI" in result
        assert "# Project Context for AI Code Review" in result

    def test_generate_fallback_context_missing_sections(self) -> None:
        """Test _generate_fallback_context with missing sections."""
        engine = TemplateEngine()

        section_content = {"project_overview": "Test overview"}

        result = engine._generate_fallback_context(section_content)

        # Should contain available content
        assert "Test overview" in result
        # Should contain project overview section but not other sections since they're missing
        assert "## Project Overview" in result
        # Should NOT contain tech stack or structure sections since they're not provided
        assert "## Technology Stack" not in result
        assert "## Architecture & Code Organization" not in result

    # ===== Main Render Method Tests =====

    def test_render_context_basic(self) -> None:
        """Test basic render_context functionality."""
        engine = TemplateEngine()

        section_content = {
            "project_overview": "Test project",
            "tech_stack": "Python",
            "code_structure": "Standard structure",
            "review_focus": "Focus areas",
            "context7_analysis": "Library docs",
        }

        facts = {
            "project_info": {"name": "test-project", "type": "python"},
        }

        result = engine.render_context(section_content, facts)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Test project" in result
        assert "Python" in result
        assert "Standard structure" in result

    def test_render_context_with_output_path(self) -> None:
        """Test render_context with output path."""
        engine = TemplateEngine()

        section_content = {"project_overview": "Test content"}
        facts = {"project_info": {"name": "test"}}

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "output.md"

            result = engine.render_context(section_content, facts, output_path)

            assert isinstance(result, str)
            assert "Test content" in result

    def test_render_context_template_load_error(self) -> None:
        """Test render_context when template loading fails."""
        engine = TemplateEngine()

        section_content = {"project_overview": "Test content"}
        facts = {"project_info": {"name": "test"}}

        with patch.object(
            engine, "_load_template", side_effect=Exception("Template error")
        ):
            result = engine.render_context(section_content, facts)

            # Should fall back to basic generation
            assert "Test content" in result
            assert "# Project Context for AI Code Review" in result
