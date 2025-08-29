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


def create_review_chain(llm: Any) -> Any:
    """Create code review chain."""
    prompt = create_review_prompt()

    return (
        {
            "system_prompt": lambda x: create_system_prompt(),
            "diff_content": lambda x: x["diff"],
            "language_hint_section": lambda x: f"**Primary Language:** {x['language']}"
            if x.get("language")
            else "",
            "project_context_section": lambda x: f"## Project Context\n{x['context']}"
            if x.get("context") and x["context"].strip()
            else "",
        }
        | prompt
        | llm
        | StrOutputParser()
    )


def create_summary_chain(llm: Any) -> Any:
    """Create MR summary chain."""
    prompt = create_summary_prompt()

    return (
        {
            "system_prompt": lambda x: create_system_prompt(),
            "diff_content": lambda x: x["diff"],
            "project_context_section": lambda x: f"## Project Context\n{x['context']}"
            if x.get("context") and x["context"].strip()
            else "",
        }
        | prompt
        | llm
        | StrOutputParser()
    )
