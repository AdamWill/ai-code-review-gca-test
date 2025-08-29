"""LangChain prompt templates and chains for AI code review."""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def create_system_prompt() -> str:
    """Create system prompt for code review."""
    return """You are an expert senior software engineer and a meticulous code reviewer.
Your goal is to provide concise, high-quality, constructive feedback on merge requests to help developers improve their code.
You need to focus on review ONLY the changes in the diff, not the entire codebase.
Your tone should be helpful, collaborative, and professional.
You must adhere strictly to the response format requested in the user's prompt."""


def create_review_prompt() -> ChatPromptTemplate:
    """Create code review prompt template."""
    template = """Please review the following code changes from a merge request.

{language_hint_section}

{project_context_section}

## Guidelines

- **Focus on High-Level Feedback:** Concentrate on logic, correctness, security vulnerabilities, performance bottlenecks, architectural patterns, and readability.
- **Ignore Trivial Issues:** Do not comment on minor stylistic issues, formatting, or things a linter would automatically catch.
- **Be Actionable:** Provide clear, concise, and actionable suggestions. Explain *why* a change is recommended.
- **Provide Code Snippets:** When suggesting a change, include a small code snippet to illustrate your point.

## Response Format

Structure your feedback in Markdown using collapsible sections as follows:

### General Feedback

A brief, high-level overview of the merge request. Mention the overall quality and any major architectural points.

### 📂 File Reviews

For each file with significant feedback, use this collapsible format:

<details>
<summary><strong>📄 `path/to/file.ext`</strong> - Brief summary of main issues</summary>

- **[Review]** A concise, actionable review. Explain the reasoning behind it.
- **[Question]** Ask a clarifying question about a piece of code. ONLY if necessary.
- **[Suggestion]** A suggestion for a change to the code. ONLY if necessary.
- **[Comment]** A comment about the code. ONLY if necessary.

</details>

### ✅ Summary

- **Overall Assessment:** Quality rating and key recommendations
- **Priority Issues:** Most critical items to address
- **Minor Suggestions:** Optional improvements

 ---

 {diff_content}"""

    return ChatPromptTemplate.from_messages(
        [("system", "{system_prompt}"), ("human", template)]
    )


def create_summary_prompt() -> ChatPromptTemplate:
    """Create MR summary prompt template."""
    template = """Based on the code diff below, please provide a concise, high-level summary of the merge request. The summary should be easy for a project manager or a new team member to understand.

{project_context_section}

## Response Format

<details>
<summary><strong>📋 MR Summary</strong> A single, descriptive sentence summarizing the change.</summary>

- **Key Changes:** A bulleted list of the most important changes.
- **Impact:** Briefly describe the impacted modules, components, or user-facing functionality.
- **Risk Level:** Low/Medium/High - Brief justification

</details>

{diff_content}"""

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
    return input_data["diff"]


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
        return f"## Project Context\n{context}"
    return ""


def _get_system_prompt(input_data: dict[str, Any]) -> str:
    """Get system prompt (ignores input data, always returns same prompt).

    Args:
        input_data: Unused, but required for LangChain compatibility

    Returns:
        The system prompt string
    """
    return create_system_prompt()


def _build_chain_inputs_for_review() -> dict[str, Any]:
    """Build input transformation functions for review chain.

    Returns:
        Dictionary mapping template variables to transformation functions
    """
    return {
        "system_prompt": _get_system_prompt,
        "diff_content": _extract_diff_content,
        "language_hint_section": _create_language_hint_section,
        "project_context_section": _create_project_context_section,
    }


def _build_chain_inputs_for_summary() -> dict[str, Any]:
    """Build input transformation functions for summary chain.

    Returns:
        Dictionary mapping template variables to transformation functions
    """
    return {
        "system_prompt": _get_system_prompt,
        "diff_content": _extract_diff_content,
        "project_context_section": _create_project_context_section,
    }


def create_review_chain(llm: Any) -> Any:
    """Create a LangChain pipeline for code review.

    This function creates a processing pipeline that:
    1. Takes input data (diff, language, context)
    2. Transforms it into template variables
    3. Applies the review prompt template
    4. Passes through the LLM
    5. Parses the output as string

    Args:
        llm: Language model instance to use for generating reviews

    Returns:
        LangChain pipeline ready to process review requests

    Example:
        >>> chain = create_review_chain(my_llm)
        >>> result = chain.invoke({
        ...     "diff": "- old code\n+ new code",
        ...     "language": "Python",
        ...     "context": "This is a web API project"
        ... })
    """
    prompt_template = create_review_prompt()
    input_transformations = _build_chain_inputs_for_review()

    # Create LangChain pipeline: input_transformations -> prompt -> llm -> parser
    chain = input_transformations | prompt_template | llm | StrOutputParser()

    return chain


def create_summary_chain(llm: Any) -> Any:
    """Create a LangChain pipeline for MR summaries.

    This function creates a processing pipeline that:
    1. Takes input data (diff, context)
    2. Transforms it into template variables
    3. Applies the summary prompt template
    4. Passes through the LLM
    5. Parses the output as string

    Args:
        llm: Language model instance to use for generating summaries

    Returns:
        LangChain pipeline ready to process summary requests

    Example:
        >>> chain = create_summary_chain(my_llm)
        >>> result = chain.invoke({
        ...     "diff": "- old code\n+ new code",
        ...     "context": "This is a web API project"
        ... })
    """
    prompt_template = create_summary_prompt()
    input_transformations = _build_chain_inputs_for_summary()

    # Create LangChain pipeline: input_transformations -> prompt -> llm -> parser
    chain = input_transformations | prompt_template | llm | StrOutputParser()

    return chain
