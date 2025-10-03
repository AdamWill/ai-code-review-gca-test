"""Project overview section for code review context."""

from __future__ import annotations

from typing import Any

from context_generator.sections.base_section import BaseSection


class OverviewSection(BaseSection):
    """Generate project overview using LLM analysis (no code samples)."""

    def __init__(self, llm_analyzer: Any) -> None:
        """Initialize overview section."""
        super().__init__("overview", required=True)
        self.llm_analyzer = llm_analyzer

    async def generate_content(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> str:
        """Generate project overview content."""
        prompt = self._create_overview_prompt(facts)
        result = await self.llm_analyzer.call_llm(prompt, self.get_template_key())
        return str(result)

    def get_template_key(self) -> str:
        """Get template key for overview section."""
        return "project_overview"

    def get_dependencies(self) -> list[str]:
        """Required facts for overview."""
        return ["project_info", "dependencies", "tech_indicators"]

    def _create_overview_prompt(self, facts: dict[str, Any]) -> str:
        """Create focused prompt for project overview."""
        project_info = facts.get("project_info", {})
        deps = facts.get("dependencies", {})
        tech = facts.get("tech_indicators", {})

        return f"""Based on this project information, create a concise overview for code reviewers.

PROJECT INFO:
- Name: {project_info.get("name", "Unknown")}
- Type: {project_info.get("type", "Unknown")}
- Description: {project_info.get("description", "No description")}

DEPENDENCIES:
- Runtime: {", ".join(deps.get("runtime", [])[:8])}
- Frameworks: {", ".join(deps.get("frameworks", []))}

TECHNOLOGY INDICATORS:
- Languages: {", ".join(tech.get("languages", []))}
- Architecture: {", ".join(tech.get("architecture", []))}

Generate EXACTLY this format:

**Purpose:** [One clear sentence about what this project does]
**Type:** [CLI tool/web service/library/application - be specific]
**Domain:** [Business/technical domain this operates in]
**Key Dependencies:** [Top 3-4 most important dependencies for understanding the codebase]

Requirements:
- Focus on what code reviewers need to understand the project
- Be specific about the actual purpose, not generic descriptions
- Mention key dependencies that affect code patterns
- Keep each line under 120 characters"""
