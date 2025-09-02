# AI Code Review Tool - Project Context

## Project Overview
AI-powered code review tool that integrates with GitLab to provide automated, intelligent code reviews using multiple AI providers (Ollama, Gemini, Anthropic). Designed for both CI/CD automation and local development workflows.

## Technology Stack
- **Language:** Python 3.12+
- **Package Manager:** uv (modern, fast Python package manager)
- **CLI Framework:** click for command-line interface
- **Configuration:** pydantic-settings for type-safe configuration management
- **AI Integration:** LangChain for AI provider abstraction
- **Testing:** pytest with comprehensive mocking of external services
- **Linting & Formatting:** ruff for fast linting and formatting
- **Type Checking:** mypy for static type analysis
- **Logging:** structlog for structured, contextual logging

## Architecture & Design Patterns
- **Clean Architecture:** Distinct separation between CLI, Core logic, Models, Providers, and Utils
- **Provider Pattern:** Abstract base provider with concrete implementations for different AI services
- **Configuration-Driven:** All behavior controlled through environment variables and CLI flags
- **Async-First:** Extensive use of async/await for I/O operations (GitLab API, AI APIs)
- **Error Handling:** Custom exception hierarchy with user-friendly error messages

## Code Style & Guidelines
- **PEP 8 Compliance:** Enforced through ruff formatting
- **Type Safety:** Mandatory type annotations with `from __future__ import annotations`
- **Docstrings:** Google-style docstrings for all public functions and classes
- **Import Organization:** Follow isort conventions, group by standard/third-party/local
- **Error Messages:** Provide actionable error messages with helpful suggestions
- **Logging:** Use structured logging with relevant context (project_id, mr_iid, provider, etc.)

## Quality Standards
- **Test Coverage:** Target 90%+ coverage on critical paths
- **External Dependencies:** Mock all external services (GitLab API, AI providers) in tests
- **Performance:** Reviews should complete within 30 seconds for typical MRs
- **Reliability:** Graceful degradation when services are unavailable
- **Cost Optimization:** Use adaptive context windows to minimize AI token usage

## Review Focus Areas
- **Security:** Validate API token handling, ensure no sensitive data in logs
- **Performance:** Check for blocking operations in async code, efficient diff processing
- **Error Handling:** Ensure comprehensive exception handling with user-friendly messages
- **Configuration:** Validate environment variable handling and default value management
- **AI Integration:** Review prompt engineering and token management strategies
- **GitLab Integration:** Check API usage patterns and rate limit handling

## Common Issues & Gotchas
- **Intentional "Bad" Patterns:**
  - Long prompt templates in `utils/prompts.py` (now organized as constants) are necessary for AI quality
  - Complex token calculations are required for different provider limits
  - Hardcoded model names in `config.py` are provider-specific defaults

- **External Dependencies Not in Diff:**
  - GitLab API structure varies between instances (gitlab.com vs self-hosted)
  - AI provider response formats differ and require specific parsing
  - LangChain abstractions hide provider-specific error handling

- **Configuration & Environment:**
  - `dry_run=True` throughout tests prevents actual API calls and costs
  - SSL verification disabled in tests is for mocking, not production
  - Large timeout values are for slow AI model inference times

- **Performance & Architecture:**
  - Synchronous file I/O in context loading is acceptable (small files)
  - No database - all data comes from GitLab API in real-time
  - Token counting approximations are sufficient for cost estimation

## Domain-Specific Context
- **GitLab Compatibility:** Support both GitLab.com and self-hosted instances with custom SSL
- **Multi-Provider Support:** Seamlessly switch between Ollama (local), Gemini, and Anthropic
- **CI/CD Integration:** Automatic detection of GitLab CI environment variables
- **File Filtering:** Smart exclusion of lockfiles, build artifacts, and binary files
- **Diff Processing:** Efficient handling of large diffs with adaptive context windows
