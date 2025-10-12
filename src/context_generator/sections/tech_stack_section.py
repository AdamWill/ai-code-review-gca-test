"""Technology stack section for code review context."""

from __future__ import annotations

from typing import Any

from context_generator.sections.base_section import BaseSection


class TechStackSection(BaseSection):
    """Generate technology stack analysis (no code samples needed)."""

    def __init__(self, llm_analyzer: Any) -> None:
        """Initialize tech stack section."""
        super().__init__("tech_stack", required=True)
        self.llm_analyzer = llm_analyzer

    async def generate_content(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> str:
        """Generate tech stack content."""
        prompt = self._create_tech_stack_prompt(facts)
        result = await self.llm_analyzer.call_llm(prompt, self.get_template_key())
        return str(result)

    def get_template_key(self) -> str:
        """Get template key for tech stack section."""
        return "tech_stack"

    def get_dependencies(self) -> list[str]:
        """Required facts for tech stack."""
        return ["dependencies", "tech_indicators", "file_structure"]

    def _create_tech_stack_prompt(self, facts: dict[str, Any]) -> str:
        """Create focused prompt for tech stack analysis."""
        deps = facts.get("dependencies", {})
        tech = facts.get("tech_indicators", {})
        structure = facts.get("file_structure", {})

        return f"""Analyze this technology stack for code review context.

DEPENDENCIES:
Runtime: {deps.get("runtime", [])}
Frameworks: {deps.get("frameworks", [])}
Testing: {deps.get("testing", [])}
Dev Tools: {deps.get("dev", [])}

TECHNOLOGY INDICATORS:
Languages: {tech.get("languages", [])}
Architecture: {tech.get("architecture", [])}
Tools: {tech.get("tools", [])}
CI/CD: {tech.get("ci_cd", [])}
Quality Tools: {tech.get("quality_tools", [])}

FILE STRUCTURE:
Config Files: {structure.get("config_files", [])}
File Counts: {structure.get("file_counts", {})}
Source Directories: {structure.get("source_dirs", [])}

Generate EXACTLY this format:

### Core Technologies
- **Primary Language:** [Language with version if available]
- **Framework/Runtime:** [Main framework or runtime environment]
- **Architecture Pattern:** [Async, MVC, Clean Architecture, etc.]

### Key Dependencies (for Context7 & API Understanding)
- **[Dependency Name with Version]** - [Why it's important for code review]
- **[Dependency Name with Version]** - [Why it's important for code review]
- **[Dependency Name with Version]** - [Why it's important for code review]

### Development Tools & CI/CD
- **Testing:** [Test framework and coverage requirements]
- **Code Quality:** [Linters, formatters, type checkers with specific tools]
- **Build/Package:** [Build system and package manager]
- **CI/CD:** [Platform name from CI/CD list] - [Key configuration patterns]
  (REQUIRED if ci_cd list is not empty, otherwise write "None detected")

Requirements:
- Include ACTUAL version constraints from dependencies (>=, ==, etc.)
- Focus on dependencies that affect code patterns and review priorities
- Mention specific tools detected (ruff, mypy, pytest, etc.)
- Include CI/CD information if present
- Maximum 6 key dependencies, prioritize most impactful ones"""
