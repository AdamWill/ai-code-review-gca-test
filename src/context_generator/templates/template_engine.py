"""Template engine for consistent context rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class TemplateEngine:
    """Renders context using template with section content."""

    def __init__(self) -> None:
        """Initialize template engine."""
        self.template_path = Path(__file__).parent / "context_template.md"

    def render_context(
        self,
        section_content: dict[str, str],
        facts: dict[str, Any],
        output_path: Path | None = None,
    ) -> str:
        """Render complete context from sections and facts."""
        try:
            # Load base template
            template = self._load_template()

            # Check if we need to preserve existing sections and manual content
            existing_sections = {}
            existing_manual_content = ""
            if output_path and output_path.exists():
                existing_sections = self._extract_existing_sections(output_path)
                existing_manual_content = self._extract_manual_sections(output_path)

            # Merge new content with existing sections (new content takes priority)
            merged_content = {**existing_sections, **section_content}

            # Apply section content
            rendered = self._apply_sections(template, merged_content)

            # Add any additional context from facts if needed
            rendered = self._add_metadata(rendered, facts)

            # Append preserved manual content if it exists
            if existing_manual_content:
                rendered = self._merge_manual_sections(
                    rendered, existing_manual_content
                )

            return rendered.strip()

        except OSError as e:
            logger.error("Template file I/O error", error=str(e))
            return self._generate_fallback_context(section_content)
        except (KeyError, ValueError) as e:
            logger.error("Template content error", error=str(e))
            return self._generate_fallback_context(section_content)
        except Exception as e:
            logger.error("Unexpected template rendering error", error=str(e))
            # For unexpected errors, include error info in the output
            error_context = f"\n\n<!-- TEMPLATE ERROR: {str(e)} -->\n"
            fallback = self._generate_fallback_context(section_content)
            return fallback + error_context

    def _load_template(self) -> str:
        """Load the base template."""
        try:
            with open(self.template_path, encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeDecodeError) as e:
            logger.error("Failed to load template", error=str(e))
            return self._get_default_template()
        except Exception as e:
            logger.error("Unexpected error loading template", error=str(e))
            return self._get_default_template()

    def _apply_sections(self, template: str, section_content: dict[str, str]) -> str:
        """Apply section content to template placeholders."""
        rendered = template

        # Replace template placeholders with actual content
        placeholder_mapping = {
            "{{project_overview}}": section_content.get(
                "project_overview", "*Overview not available*"
            ),
            "{{tech_stack}}": section_content.get(
                "tech_stack", "*Tech stack not available*"
            ),
            "{{code_structure}}": section_content.get(
                "code_structure", "*Structure not available*"
            ),
            "{{review_focus}}": section_content.get(
                "review_focus", "*Review focus not available*"
            ),
            "{{context7_analysis}}": section_content.get(
                "context7_analysis", "*Library documentation not available*"
            ),
            "{{ci_docs_analysis}}": section_content.get(
                "ci_docs_analysis", "*CI/CD documentation not available*"
            ),
        }

        for placeholder, content in placeholder_mapping.items():
            rendered = rendered.replace(placeholder, content)

        return rendered

    def _add_metadata(self, rendered: str, facts: dict[str, Any]) -> str:
        """Add minimal metadata if needed (avoid clutter for reviewers)."""
        # Only add essential metadata that helps reviewers
        project_info = facts.get("project_info", {})
        project_name = project_info.get("name", "Unknown Project")

        # Replace project name if template has placeholder
        rendered = rendered.replace("{{project_name}}", project_name)

        return rendered

    def _get_default_template(self) -> str:
        """Get default template if file loading fails."""
        return """# Project Context for AI Code Review

## Project Overview
{{project_overview}}

## Technology Stack
{{tech_stack}}

## Architecture & Code Organization
{{code_structure}}

## Code Review Focus Areas
{{review_focus}}"""

    def _generate_fallback_context(self, section_content: dict[str, str]) -> str:
        """Generate basic context if template rendering fails."""
        context_parts = ["# Project Context for AI Code Review\n"]

        # Add available sections
        if "project_overview" in section_content:
            context_parts.extend(
                ["## Project Overview", section_content["project_overview"], ""]
            )

        if "tech_stack" in section_content:
            context_parts.extend(
                ["## Technology Stack", section_content["tech_stack"], ""]
            )

        if "code_structure" in section_content:
            context_parts.extend(
                [
                    "## Architecture & Code Organization",
                    section_content["code_structure"],
                    "",
                ]
            )

        if "review_focus" in section_content:
            context_parts.extend(
                ["## Code Review Focus Areas", section_content["review_focus"], ""]
            )

        if "ci_docs_analysis" in section_content:
            context_parts.extend(
                [
                    "## CI/CD Configuration Guide",
                    section_content["ci_docs_analysis"],
                    "",
                ]
            )

        return "\n".join(context_parts)

    def _extract_existing_sections(self, file_path: Path) -> dict[str, str]:
        """Extract existing automatic sections from file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            sections = {}

            # Split content at manual sections marker to only process automatic sections
            manual_marker = "<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->"
            if manual_marker in content:
                automatic_content = content[: content.find(manual_marker)]
            else:
                automatic_content = content

            # Extract each section using regex patterns
            section_patterns = {
                "project_overview": r"## Project Overview\n(.*?)(?=\n## |\n---|\Z)",
                "tech_stack": r"## Technology Stack\n(.*?)(?=\n## |\n---|\Z)",
                "code_structure": r"## Architecture & Code Organization\n(.*?)(?=\n## |\n---|\Z)",
                "review_focus": r"## Code Review Focus Areas\n(.*?)(?=\n## |\n---|\Z)",
                "ci_docs_analysis": r"## CI/CD Configuration Guide\n(.*?)(?=\n## |\n---|\Z)",
            }

            import re

            for section_key, pattern in section_patterns.items():
                match = re.search(pattern, automatic_content, re.DOTALL)
                if match:
                    section_content = match.group(1).strip()
                    # Only preserve if it's not a placeholder
                    # Placeholders typically start with "*" and end with "*" (e.g., "*Overview not available*")
                    # Real content may use markdown bold (**text**) which is different
                    is_placeholder = (
                        not section_content
                        or (
                            section_content.startswith("*")
                            and section_content.endswith("*")
                        )
                        or "not available" in section_content
                    )

                    if not is_placeholder:
                        sections[section_key] = section_content
                        logger.debug(f"Preserved existing section: {section_key}")
                    else:
                        logger.debug(f"Skipped placeholder section: {section_key}")

            return sections

        except Exception as e:
            logger.debug("Failed to extract existing sections", error=str(e))
            return {}

    def _extract_manual_sections(self, file_path: Path) -> str:
        """Extract manual sections from existing file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Look for the manual sections marker
            manual_marker = "<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->"
            if manual_marker in content:
                # Extract everything after the marker
                manual_start = content.find(manual_marker)
                manual_content = content[manual_start:]
                logger.debug(
                    "Preserved manual sections", content_length=len(manual_content)
                )
                return manual_content

            return ""

        except Exception as e:
            logger.debug("Failed to extract manual sections", error=str(e))
            return ""

    def _merge_manual_sections(self, rendered: str, manual_content: str) -> str:
        """Merge preserved manual sections with newly rendered content."""
        # Remove the template manual sections and replace with preserved content
        manual_marker = "<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->"

        if manual_marker in rendered:
            # Find where manual sections start in the rendered content
            manual_start = rendered.find(manual_marker)
            # Keep everything before the marker and append the preserved content
            return rendered[:manual_start] + manual_content
        else:
            # If no marker in rendered content, append manual sections
            return rendered + "\n\n" + manual_content
