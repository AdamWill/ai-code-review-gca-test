"""Review focus section with code-based recommendations."""

from __future__ import annotations

from typing import Any

from context_generator.sections.base_section import BaseSection


class ReviewFocusSection(BaseSection):
    """Generate code review focus areas based on actual code patterns."""

    def __init__(self, llm_analyzer: Any) -> None:
        """Initialize review focus section."""
        super().__init__("review_focus", required=True)
        self.llm_analyzer = llm_analyzer

    async def generate_content(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> str:
        """Generate review focus content with code analysis."""
        prompt = self._create_review_focus_prompt(facts, code_samples)
        result = await self.llm_analyzer.call_llm(prompt, self.get_template_key())
        return str(result)

    def get_template_key(self) -> str:
        """Get template key for review focus section."""
        return "review_focus"

    def get_dependencies(self) -> list[str]:
        """Required facts for review focus."""
        return ["dependencies", "tech_indicators"]

    def _create_review_focus_prompt(
        self, facts: dict[str, Any], code_samples: dict[str, str]
    ) -> str:
        """Create prompt for review focus analysis."""
        deps = facts.get("dependencies", {})
        tech = facts.get("tech_indicators", {})

        # Format code samples for LLM
        code_samples_text = ""
        for sample_type, content in code_samples.items():
            code_samples_text += f"\n=== {sample_type.upper()} ===\n{content}\n"

        return f"""Based on this project's tech dependencies and code patterns, recommend specific areas for code review focus.

TECHNOLOGY CONTEXT:
Runtime Dependencies: {deps.get("runtime", [])}
Frameworks: {deps.get("frameworks", [])}
Languages: {tech.get("languages", [])}
Architecture Indicators: {tech.get("architecture", [])}

ACTUAL CODE SAMPLES:
{code_samples_text}

Generate EXACTLY 4-5 focus areas in this format:

- **[Specific Technical Area]** - [What to look for based on this tech stack and code patterns]
- **[Architecture/Pattern Area]** - [What to verify based on observed architectural patterns]
- **[Framework-Specific Area]** - [What to check based on key dependencies used]
- **[Code Quality Area]** - [What standards to enforce based on project conventions]
- **[Domain-Specific Area]** - [What to focus on based on project's business domain]

Requirements:
- Base recommendations on ACTUAL code patterns observed in samples
- Be specific to the technologies and frameworks detected
- Focus on things reviewers might miss without full project context
- Mention specific patterns, anti-patterns, or conventions to check
- Each area should be actionable and specific to this codebase
- Avoid generic advice that applies to all projects"""
