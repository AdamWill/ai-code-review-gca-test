"""Simple tests for TemplateEngine functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path

from context_generator.templates.template_engine import TemplateEngine


class TestTemplateEngineSimple:
    """Simple tests for TemplateEngine functionality."""

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

    def test_extract_existing_sections_no_file(self) -> None:
        """Test _extract_existing_sections with non-existent file."""
        engine = TemplateEngine()

        non_existent_path = Path("/tmp/non_existent_file.md")
        sections = engine._extract_existing_sections(non_existent_path)

        assert isinstance(sections, dict)
        assert len(sections) == 0

    def test_extract_manual_sections_no_marker(self) -> None:
        """Test _extract_manual_sections without manual marker."""
        engine = TemplateEngine()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Project Context

## Overview
Some content without manual sections
""")
            f.flush()

            manual_content = engine._extract_manual_sections(Path(f.name))

            assert manual_content == ""

            # Clean up
            Path(f.name).unlink()

    def test_extract_manual_sections_with_marker(self) -> None:
        """Test _extract_manual_sections with manual marker."""
        engine = TemplateEngine()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Project Context

## Overview
Auto-generated content

<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->

### Custom Notes
These are custom notes that should be preserved.
""")
            f.flush()

            manual_content = engine._extract_manual_sections(Path(f.name))

            assert "Custom Notes" in manual_content
            assert "preserved" in manual_content

            # Clean up
            Path(f.name).unlink()

    def test_merge_manual_sections(self) -> None:
        """Test _merge_manual_sections method."""
        engine = TemplateEngine()

        base_content = """# Project Context

## Overview
New overview content

## Structure
New structure content
"""

        manual_content = """### Custom Notes
These are preserved notes.
"""

        result = engine._merge_manual_sections(base_content, manual_content)

        # Should contain both base and manual content
        assert "New overview content" in result
        assert "New structure content" in result
        assert "Custom Notes" in result
        assert "preserved notes" in result

    def test_render_context_new_file(self) -> None:
        """Test render_context for new file."""
        engine = TemplateEngine()

        section_content = {
            "project_overview": "Test project overview",
            "code_structure": "Simple structure",
            "tech_stack": "Python, pytest",
            "review_focus": "Focus on testing",
        }

        facts = {
            "project_info": {"name": "test-project"},
            "dependencies": {"runtime": []},
        }

        result = engine.render_context(section_content, facts)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_context_error_handling(self) -> None:
        """Test render_context error handling."""
        engine = TemplateEngine()

        # Test with invalid template path
        original_path = engine.template_path
        engine.template_path = Path("/non/existent/template.md")

        try:
            result = engine.render_context({}, {})

            # Should return fallback content
            assert isinstance(result, str)
            assert len(result) > 0

        finally:
            # Restore original path
            engine.template_path = original_path
