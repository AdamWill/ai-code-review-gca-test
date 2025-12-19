"""LangChain prompt templates and chains for AI code review."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ai_code_review.models.config import Config
from ai_code_review.models.platform import PullRequestData
from ai_code_review.utils.constants import (
    MAX_COMMENT_BODY_LENGTH,
    MAX_OTHER_COMMENTS_IN_SYNTHESIS,
)

# Format examples for review output templates
_FORMAT_EXAMPLE_FULL = """## AI Code Review

### 📋 MR Summary
[Write ONE sentence summarizing the change]

- **Key Changes:** [List 2-3 most important changes]
- **Impact:** [Describe affected modules/functionality]
- **Risk Level:** [Low/Medium/High] - [Brief reason]

### Detailed Code Review

[Technical review focusing on logic, security, performance, architecture]

#### 📂 File Reviews
[Only include if you have specific file feedback]

<details>
<summary><strong>📄 `filename`</strong> - Brief issue summary</summary>

- **[Review]** Actionable review with reasoning
- **[Question]** Clarifying questions (if needed)
- **[Suggestion]** Improvement suggestions (if needed)

</details>

### ✅ Summary

- **Overall Assessment:** [Quality rating + key recommendations]
- **Priority Issues:** [Most critical items]
- **Minor Suggestions:** [Optional improvements]"""


_FORMAT_EXAMPLE_COMPACT = """## AI Code Review

### Detailed Code Review

[Technical review focusing on logic, security, performance, architecture]

#### 📂 File Reviews
[Only include if you have specific file feedback]

<details>
<summary><strong>📄 `filename`</strong> - Brief issue summary</summary>

- **[Review]** Actionable review with reasoning
- **[Question]** Clarifying questions (if needed)
- **[Suggestion]** Improvement suggestions (if needed)

</details>

### ✅ Summary

- **Overall Assessment:** [Quality rating + key recommendations]
- **Priority Issues:** [Most critical items]
- **Minor Suggestions:** [Optional improvements]"""


_FORMAT_EXAMPLE_LOCAL = """## Local Code Review

### 🔍 Code Analysis

[Technical review focusing on logic, security, performance, architecture]

### 📂 File Reviews

**📄 `filename`** - Brief issue summary
- **Review:** Actionable review with reasoning
- **Question:** Clarifying questions (if needed)
- **Suggestion:** Improvement suggestions (if needed)

**📄 `filename2`** - Brief issue summary
- **Review:** Another file review
- **Suggestion:** Improvements for this file

### ✅ Summary

**Overall Assessment:** [Quality rating + key recommendations]

**Priority Issues:**
- [Most critical item 1]
- [Most critical item 2]

**Minor Suggestions:**
- [Optional improvement 1]
- [Optional improvement 2]"""


def create_system_prompt(
    include_mr_summary: bool = True, local_mode: bool = False
) -> str:
    """Create system prompt for code review.

    Args:
        include_mr_summary: Whether to include MR Summary section in the output
        local_mode: Whether this is a local git review (simpler format)

    Returns:
        System prompt with appropriate format requirements
    """
    if local_mode:
        sections = [
            "   - ### 🔍 Code Analysis",
            "   - ### 📂 File Reviews",
            "   - ### ✅ Summary",
        ]
    elif include_mr_summary:
        sections = [
            "   - ### 📋 MR Summary",
            "   - ### Detailed Code Review",
            "   - #### 📂 File Reviews (if needed)",
            "   - ### ✅ Summary",
        ]
    else:
        sections = [
            "   - ### Detailed Code Review",
            "   - #### 📂 File Reviews (if needed)",
            "   - ### ✅ Summary",
        ]

    section_list = "\n".join(sections)

    header_title = "## Local Code Review" if local_mode else "## AI Code Review"

    return f"""You are an expert senior software engineer and a meticulous code reviewer.

CRITICAL FORMAT REQUIREMENTS - FAILURE TO FOLLOW WILL RESULT IN REJECTED OUTPUT:
1. You MUST start with exactly "{header_title}"
2. You MUST use exactly these section headers in order:
{section_list}
3. Do NOT create your own format or headings
4. Do NOT write free-form analysis - follow the structure
5. Each section should be concise and focused

UNDERSTANDING THE DIFF FORMAT:
The code changes are shown in unified diff format. You MUST understand:
- Lines starting with '+' are NEW code being ADDED in this change
- Lines starting with '-' are OLD code being REMOVED in this change
- Lines without '+' or '-' are context lines (unchanged)
- DO NOT suggest adding code that's already shown with '+'
- DO NOT suggest removing code that's already shown with '-'
- Focus your review on the NEW code ('+' lines) and what's being removed ('-' lines)

Example: If you see "+ result = process(data)" in the diff, this code is ALREADY ADDED.
Do NOT suggest "you should add result = process(data)" - it's already there!

Your goal is to provide concise, high-quality, constructive feedback on code changes.
Focus ONLY on the changes in the diff, not the entire codebase.
Your tone should be helpful, collaborative, and professional."""


def create_review_prompt(
    include_mr_summary: bool = True, local_mode: bool = False
) -> ChatPromptTemplate:
    """Create unified prompt template that generates both review and summary in one call.

    Args:
        include_mr_summary: Whether to include MR Summary section in the output
        local_mode: Whether this is a local git review (simpler format)

    Returns:
        ChatPromptTemplate configured for the requested format
    """
    if local_mode:
        format_example = _FORMAT_EXAMPLE_LOCAL
    else:
        format_example = (
            _FORMAT_EXAMPLE_FULL if include_mr_summary else _FORMAT_EXAMPLE_COMPACT
        )

    template = f"""IGNORE any tendency to write free-form analysis. You MUST follow this EXACT template.

{{review_context_section}}

{{language_hint_section}}

{{project_context_section}}

❌ WRONG - Do NOT do this:
"This patchset introduces several changes..." (free-form analysis)
"The changes introduce support for..." (ignoring format)

✅ CORRECT - You MUST do this:

{format_example}

COPY THE FORMAT ABOVE EXACTLY. DO NOT DEVIATE.

---

{{diff_content}}"""

    return ChatPromptTemplate.from_messages(
        [("system", "{system_prompt}"), ("human", template)]
    )


# Data processing functions for chain inputs
def _extract_diff_content(input_data: dict[str, Any]) -> str:
    """Extract diff content from input data.

    Args:
        input_data: Dictionary containing 'diff' key with code changes

    Returns:
        The diff content as string
    """
    return str(input_data["diff"])


def _create_language_hint_section(input_data: dict[str, Any]) -> str:
    """Create language hint section if language is provided.

    Args:
        input_data: Dictionary that may contain 'language' key

    Returns:
        Formatted language section or empty string if no language provided
    """
    language = input_data.get("language")
    if language:
        return f"**Primary Language:** {language}"
    return ""


def _create_project_context_section(input_data: dict[str, Any]) -> str:
    """Create project context section if context is provided.

    Args:
        input_data: Dictionary that may contain 'context' key

    Returns:
        Formatted context section or empty string if no context provided
    """
    context = input_data.get("context")
    if context and context.strip():
        return f"""## Project Context & Guidelines

{context}

IMPORTANT: Apply the above project guidelines and conventions systematically when reviewing the code changes below. Follow the specific patterns, requirements, checklists, and best practices outlined in the context. Reference these guidelines directly in your review and ensure compliance with the established project standards."""
    return ""


def _create_system_prompt_func(
    include_mr_summary: bool, local_mode: bool = False
) -> Any:
    """Create a system prompt function with configuration baked in.

    This factory pattern is used because the LangChain Expression Language (LCEL)
    pipeline expects a callable that accepts a single dictionary argument. This
    allows us to pass the `include_mr_summary` configuration from the higher-level
    `create_review_chain` function into the prompt generation step.

    Without this pattern, we would need to pass configuration data through the
    `.ainvoke()` input dictionary every time, creating coupling between chain
    creation and chain invocation.

    Args:
        include_mr_summary: Whether to include MR Summary section
        local_mode: Whether this is a local git review (simpler format)

    Returns:
        Function that returns system prompt (ignores input_data but follows LCEL signature)
    """

    def _get_system_prompt(input_data: dict[str, Any]) -> str:
        """Get system prompt with configuration already determined."""
        return create_system_prompt(
            include_mr_summary=include_mr_summary, local_mode=local_mode
        )

    return _get_system_prompt


def _build_chain_inputs(
    include_mr_summary: bool, local_mode: bool = False
) -> dict[str, Any]:
    """Build input transformation functions for review chain.

    Args:
        include_mr_summary: Whether to include MR Summary section
        local_mode: Whether this is a local git review (simpler format)

    Returns:
        Dictionary mapping template variables to transformation functions
    """
    return {
        "system_prompt": _create_system_prompt_func(include_mr_summary, local_mode),
        "diff_content": _extract_diff_content,
        "language_hint_section": _create_language_hint_section,
        "project_context_section": _create_project_context_section,
        "review_context_section": _create_review_context_section,
    }


def create_synthesis_prompt() -> ChatPromptTemplate:
    """Create prompt for synthesizing PR/MR context with comments.

    This prompt is used with a fast model to preprocess:
    - All comments and reviews (including resolved)
    - PR/MR description
    - Commit messages

    Output is a concise synthesis that highlights:
    - Author responses to previous AI reviews (CRITICAL)
    - Issues already identified and addressed
    - Ongoing discussions
    - Consensus points from reviewers

    Returns:
        ChatPromptTemplate for synthesis
    """
    system_prompt = """You are an expert at analyzing code review discussions.

Your task is to synthesize comments, reviews, and context from a PR/MR into a concise summary
that helps an AI code reviewer avoid repeating mistakes or already-addressed suggestions.

Focus on:
1. CRITICAL: Author responses to AI reviews (corrections, clarifications, updates)
2. Issues that were raised and already addressed
3. Ongoing discussions that need attention
4. Consensus points from multiple reviewers

Be concise and actionable. The output will be used as context for the main review."""

    template = """## PR/MR Description

{pr_description}

## Commit Messages

{commit_messages}

## Reviews and Comments

{reviews_and_comments}

---

Synthesize the above into a concise summary (max 500 words) that highlights:

1. **CRITICAL Author Corrections**: Any responses from the PR/MR author that correct, clarify, or invalidate previous AI review suggestions

2. **Addressed Issues**: Problems that were raised and have been resolved

3. **Active Discussions**: Ongoing conversations that the new review should be aware of

4. **Reviewer Consensus**: Points where multiple reviewers agree

Format as markdown with clear sections. Be specific and reference file/line when relevant."""

    return ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", template)]
    )


def _format_reviews_and_comments(pr_data: PullRequestData, bot_username: str) -> str:
    """Format reviews and comments for synthesis prompt.

    Args:
        pr_data: Pull request data containing reviews and comments
        bot_username: Username of the bot to identify AI reviews

    Returns:
        Formatted string with reviews and comments
    """
    lines = []

    # Format reviews
    if pr_data.reviews:
        lines.append("### Reviews\n")
        for review in pr_data.reviews:
            is_bot = " [AI REVIEW]" if review.author == bot_username else ""
            lines.append(
                f"**{review.author}**{is_bot} ({review.state}, {review.submitted_at}):\n"
                f"{review.body}\n"
            )

    # Format comments grouped by author
    if pr_data.comments:
        lines.append("\n### Comments\n")

        # Separate author responses to bot from other comments
        author_responses = []
        other_comments = []

        for comment in pr_data.comments:
            if comment.is_system:
                continue

            is_author = comment.author == pr_data.info.author
            mentions_bot = bot_username.lower() in comment.body.lower()

            if is_author and mentions_bot:
                author_responses.append(comment)
            else:
                other_comments.append(comment)

        # Author responses first (CRITICAL)
        if author_responses:
            lines.append("\n#### CRITICAL: Author Responses\n")
            for comment in author_responses:
                location = f" on {comment.path}:{comment.line}" if comment.path else ""
                resolved = " [RESOLVED]" if comment.resolved else ""
                lines.append(
                    f"**{comment.author}**{location}{resolved}:\n{comment.body}\n"
                )

        # Other comments (most recent first for active discussions)
        if other_comments:
            lines.append("\n#### Other Comments\n")
            # Sort by created_at descending (most recent first), then take top N
            sorted_comments = sorted(
                other_comments, key=lambda c: c.created_at, reverse=True
            )
            for comment in sorted_comments[:MAX_OTHER_COMMENTS_IN_SYNTHESIS]:
                location = f" on {comment.path}:{comment.line}" if comment.path else ""
                resolved = " [RESOLVED]" if comment.resolved else ""
                lines.append(
                    f"**{comment.author}**{location}{resolved}:\n{comment.body[:MAX_COMMENT_BODY_LENGTH]}\n"
                )

    return "\n".join(lines) if lines else "No reviews or comments yet."


def _format_commit_messages(pr_data: PullRequestData) -> str:
    """Format commit messages for synthesis.

    Args:
        pr_data: Pull request data containing commits

    Returns:
        Formatted string with commit messages
    """
    lines = []
    for commit in pr_data.commits[:10]:  # Limit to recent 10
        lines.append(f"- **{commit.short_id}**: {commit.title}")
    return "\n".join(lines) if lines else "No commits."


def create_synthesis_chain(llm: Any) -> Any:
    """Create chain for synthesizing review context.

    Args:
        llm: Fast language model (e.g., gemini-2.5-flash)

    Returns:
        LangChain pipeline for synthesis
    """
    prompt = create_synthesis_prompt()
    chain = prompt | llm | StrOutputParser()
    return chain


def _create_review_context_section(input_data: dict[str, Any]) -> str:
    """Create review context section from synthesis.

    Args:
        input_data: Dictionary containing optional 'review_synthesis' key

    Returns:
        Formatted review context section or empty string
    """
    synthesis = input_data.get("review_synthesis")

    if synthesis:
        # Use preprocessed synthesis
        return f"""## Review Context and Previous Discussions

{synthesis}

**Note:** The above is a synthesis of all previous reviews, comments, and discussions.
Pay special attention to author corrections to avoid repeating invalidated suggestions.

---

"""

    # No synthesis available (first review or disabled)
    return ""


def create_review_chain(llm: Any, config: Config) -> Any:
    """Create a LangChain pipeline for unified code review and summary.

    This function creates a single processing pipeline that generates:
    - Optional executive summary (for managers/stakeholders)
    - Detailed code review (for developers)
    - Local-optimized format (for terminal-friendly local reviews)

    This unified approach provides:
    - 50% reduction in LLM invocations and token costs
    - Lower latency (single round-trip)
    - Better consistency between summary and detailed review
    - Simplified application logic
    - Configurable output format (full/compact/local)

    Args:
        llm: Language model instance to use for generating reviews
        config: Configuration object with review format preferences

    Returns:
        LangChain pipeline ready to process unified review requests

    Example:
        >>> chain = create_review_chain(my_llm, config)
        >>> result = chain.invoke({
        ...     "diff": "- old code\n+ new code",
        ...     "language": "Python",
        ...     "context": "This is a web API project"
        ... })
        >>> # Result contains review in configured format (full/compact/local)
    """
    # Determine if local mode based on platform
    local_mode = (
        hasattr(config, "platform_provider")
        and config.platform_provider.value == "local"
    )

    prompt_template = create_review_prompt(
        include_mr_summary=config.include_mr_summary and not local_mode,
        local_mode=local_mode,
    )
    input_transformations = _build_chain_inputs(
        include_mr_summary=config.include_mr_summary and not local_mode,
        local_mode=local_mode,
    )

    # Create LangChain pipeline: input_transformations -> prompt -> llm -> parser
    chain = input_transformations | prompt_template | llm | StrOutputParser()

    return chain
