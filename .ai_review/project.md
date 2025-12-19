# Project Context for AI Code Review

## Project Overview

**Purpose:** An AI-powered code review tool that analyzes local Git changes and remote pull/merge requests.
**Type:** CLI tool
**Domain:** Developer Tools & Code Analysis
**Key Dependencies:** `click` (CLI framework), `langchain` (LLM interaction), `python-gitlab`/`pygithub` (VCS APIs)

## Technology Stack

### Core Technologies
- **Primary Language:** Python
- **Framework/Runtime:** Asynchronous Command-Line Interface (CLI)
- **Architecture Pattern:** Asynchronous, src-based layout

### Key Dependencies (for Context7 & API Understanding)
- **langchain>=0.2.0** - Core dependency for building applications with Large Language Models (LLMs). Used for chains, model integrations, and prompt management across multiple AI providers (Gemini, Anthropic, Ollama).
- **click>=8.1.0** - Command-Line Interface framework. Defines CLI structure with `@click.command()` and `@click.option()` decorators.
- **httpx>=0.28.1** - Primary HTTP client library for both synchronous and asynchronous requests. Used for health checks, remote file fetching, SSL certificate downloads, and streaming diff downloads.
- **python-gitlab>=4.0.0** & **pygithub>=2.1.0** - Platform-specific API libraries for GitLab and GitHub integration. Handle authentication, MR/PR data fetching, and comment posting.
- **pydantic>=2.11.0** - Data validation and settings management. Used for configuration models, API data structures, and type enforcement throughout the application.
- **structlog>=23.2.0** - Structured logging framework. Provides consistent, context-rich logging with proper sensitive data handling.
- **aiofiles>=23.2.0** - Asynchronous file I/O operations for non-blocking file access in async contexts.

### Development Tools & CI/CD
- **Testing:** `pytest>=7.4.0` with `pytest-asyncio` for testing asynchronous code and `pytest-cov` for coverage reporting.
- **Code Quality:** `ruff>=0.1.0` for linting and formatting, and `mypy>=1.7.0` for static type checking.
- **Build/Package:** Modern Python packaging using `pyproject.toml`.
- **CI/CD:** GitLab CI/CD, configured via `.gitlab-ci.yml`.

## Architecture & Code Organization

### Project Organization
```
src/ai_code_review/
├── cli.py                  # Main entry point
├── core/
│   ├── review_engine.py    # Orchestration logic
│   ├── gitlab_client.py    # GitLab API integration
│   ├── github_client.py    # GitHub API integration
│   └── local_git_client.py # Direct Git analysis
├── models/
│   ├── config.py           # Configuration (CRITICAL)
│   ├── platform.py         # Platform data models
│   └── review.py           # Review result models
├── providers/
│   ├── base.py             # AI provider interface
│   ├── anthropic.py        # Claude integration
│   ├── gemini.py           # Gemini integration
│   └── ollama.py           # Ollama integration
└── utils/
    ├── prompts.py          # LangChain prompt templates
    ├── constants.py        # Constants and defaults
    └── exceptions.py       # Custom exceptions

tests/
├── unit/                   # Component unit tests
└── integration/            # End-to-end tests
```

### Architecture Patterns
**Code Organization:** Layered Architecture. The application is structured into distinct layers: a Command Line Interface (`cli.py`) for user interaction, a `core` layer (`review_engine.py`) for orchestrating business logic, a `providers` layer for interacting with external AI and platform APIs, and a `models` layer (`config.py`) for data structures and configuration.
**Key Components:**
- **`ReviewEngine`:** The central orchestrator in `src/ai_code_review/core/review_engine.py`. It initializes platform clients (e.g., GitLab, GitHub) and AI providers based on the configuration, and manages the end-to-end process of fetching code, generating a review, and posting it.
- **Pydantic Models:** Used extensively in `src/ai_code_review/models/config.py` and `src/context_generator/models.py`. `pydantic.BaseSettings` is used for application configuration, providing type validation and loading from environment variables. `pydantic.BaseModel` is used for data structures throughout the application.
- **Provider Abstraction:** The system uses a factory pattern (`_create_platform_client`, `_create_ai_provider` in `ReviewEngine`) and interfaces (`PlatformClientInterface`, `BaseAIProvider`) to decouple the core logic from specific implementations of AI services (Ollama) and code platforms (GitLab, GitHub).
**Entry Points:** The application is a command-line tool. The main entry point is defined in `src/ai_code_review/cli.py` using the `click` library. It parses arguments, loads the `Config` object, and instantiates and runs the `ReviewEngine`.

### Important Files for Review Context
- **`src/ai_code_review/cli.py`** - Main entry point. Processes user inputs, loads configuration, and invokes `ReviewEngine`. Review exit code handling for different error types.
- **`src/ai_code_review/models/config.py`** - **CRITICAL FILE**. Defines all application settings using Pydantic with layered configuration system. Changes here affect every component. Reviewers must verify:
  - Interdependent fields use None + getter pattern (never `default_factory`)
  - Field validators don't break config priority (CLI > Env > File > Defaults)
  - New settings have proper type hints and validation
  - Environment variable mapping works via `BaseSettings`
- **`src/ai_code_review/core/review_engine.py`** - Primary orchestration logic. Contains:
  - Two-phase review system (synthesis + main review)
  - Platform client and AI provider factory methods
  - Context loading hierarchy (team > project > commits)
  - Adaptive context window sizing
  - Skip review logic
  Changes here directly impact core review functionality.
- **`src/ai_code_review/utils/prompts.py`** - LangChain prompt templates and chain construction. v1.15.0+ includes synthesis chain for comment preprocessing. Critical for review quality.
- **`src/ai_code_review/models/platform.py`** - Platform data models including `PullRequestData`, `Review`, `ReviewComment`. Extended in v1.15.0 for comment synthesis support.
- **`src/ai_code_review/providers/base.py`** - Base provider interface. All AI providers must implement this. Includes adaptive context window methods.
- **Platform Clients**:
  - `src/ai_code_review/core/gitlab_client.py` - GitLab API integration via `python-gitlab`. Includes complete diff fetching via HTTP `.diff` endpoints with streaming parser and pre-filtering.
  - `src/ai_code_review/core/github_client.py` - GitHub API integration via `PyGithub`. Includes complete diff fetching with GitHub.com vs Enterprise URL handling.
  - `src/ai_code_review/core/local_git_client.py` - Direct Git diff analysis without platform APIs. Enhanced with pre-filtering for binary and excluded files.
  All implement `PlatformClientInterface` and support comment/review fetching (v1.15.0+)
- **`src/ai_code_review/utils/diff_parser.py`** - Streaming diff parser with intelligent pre-filtering. `FilteringStreamingDiffParser` processes diffs in chunks, filters binary files and excluded patterns before parsing content, and tracks statistics.

### Development Conventions
- **Naming:** Classes use `PascalCase` (e.g., `ReviewEngine`, `ContextResult`). Functions, methods, and variables use `snake_case` (e.g., `_resolve_project_params`). Internal helper functions are prefixed with a single underscore (`_get_enum_value`). Constants are `UPPER_SNAKE_CASE` (e.g., `AUTO_BIG_DIFFS_THRESHOLD_CHARS`).
- **Module Structure:** The project follows a `src` layout. Code is organized into feature-based packages (`ai_code_review`, `context_generator`). Within these, modules are separated by responsibility (`core`, `models`, `providers`, `utils`), promoting a clear separation of concerns.
- **Configuration:** Configuration is centralized in `src/ai_code_review/models/config.py` using `pydantic_settings.BaseSettings`. This provides strongly-typed, validated configuration that can be loaded from environment variables.
- **Testing:** The `tests/` directory is structured with separate `unit/` and `integration/` subdirectories, indicating a clear distinction between testing components in isolation and testing their interactions. The presence of `conftest.py` implies the use of `pytest` and its fixture system.

## Code Review Focus Areas

### Critical Review Areas

- **[Configuration Layer System]** - The project uses a strict layered config system: CLI > Env > File > Defaults. When reviewing changes to `models/config.py`:
  - **Never approve `default_factory` usage with field references** - this breaks the layered system
  - Verify interdependent fields use the None + getter pattern (like `ai_model` → `get_ai_model()`)
  - Ensure all code uses getter methods (`get_ai_model()`) not direct field access
  - Check that field validators don't reference other fields that haven't been initialized yet
  - Test with `Config(ai_provider=X)` to ensure defaults resolve correctly

- **[HTTP Client Consistency]** - The project standardizes on `httpx` for HTTP operations:
  - `httpx` is used for both sync and async HTTP requests throughout the codebase
  - Synchronous `httpx` operations are acceptable for initialization-time I/O (context loading, health checks)
  - Async `httpx.AsyncClient` is used for hot-path operations (streaming diff downloads, repeated API calls)
  - **Exception**: `ssl_utils.py` still uses `aiohttp` for SSL certificate downloads (legacy code)
  - **Do not introduce aiohttp in new code** - `httpx` handles all our HTTP needs (sync, async, streaming)

- **[Asynchronous API Integration]** - Platform clients use async I/O for API calls:
  - Review `async`/`await` usage in `GitLabClient`, `GitHubClient`, `LocalGitClient`
  - Verify blocking operations are wrapped with `asyncio.to_thread()` when necessary
  - Check that `ClientSession` objects are managed in async context managers
  - Ensure platform-specific API calls follow provider patterns (GitLab uses `python-gitlab`, GitHub uses `PyGithub`)

- **[Provider Abstraction and Factory Pattern]** - The `ReviewEngine` uses factory methods for dependency injection:
  - Verify new providers implement `PlatformClientInterface` or `BaseAIProvider`
  - Check factory logic in `_create_platform_client()` and `_create_ai_provider()`
  - Ensure provider-specific logic stays in provider classes, not in `ReviewEngine`
  - Review model override support (e.g., `_create_ai_provider(model_override="...")` for synthesis)

- **[LangChain Prompt and Chain Management]** - Review synthesis and main review chains:
  - Scrutinize changes to prompt templates in `utils/prompts.py`
  - Verify chain construction: `prompt | model | output_parser`
  - Check context formatting for review synthesis phase (filters bot comments, author prioritization)
  - Ensure model parameters (temperature, max_tokens, num_ctx) are passed correctly
  - Review output handling - synthesis produces string, main review produces structured markdown

- **[Context Loading Hierarchy]** - Team context > Project context > Commit history:
  - Verify `team_context_file` is loaded before `project_context_file`
  - Check URL validation for remote context files (must be http:// or https://)
  - Ensure local file paths are handled with `os.path.isfile()` checks
  - Remote loading uses `httpx` (synchronous is acceptable - happens once at startup)
  - Error handling must log warnings but not fail the review if context unavailable

- **[Pydantic Configuration and Validation]** - Strict validation prevents misconfiguration:
  - All new settings in `models/config.py` must have type hints and validators
  - Use `field_validator` for single-field validation, `model_validator` for cross-field
  - Test with invalid inputs to ensure proper error messages
  - Verify environment variable mapping works via `BaseSettings`
  - Check that None/empty string values are handled correctly (use `.strip()`)

- **[Custom Exception Handling and Exit Codes]** - Exceptions map to specific exit codes:
  - `ReviewSkippedError` → exit 0 (intentional skip, not an error)
  - `PlatformAPIError` → exit 1 (API failure)
  - `AIProviderError` → exit 1 (LLM failure)
  - Review that exceptions are raised in correct business logic (not in platform clients)
  - Ensure exceptions are caught in `cli.py` and converted to appropriate exit codes
  - Verify error messages are user-friendly and actionable

### Secondary Review Areas

- **[Complete Diff Fetching System]** - Streaming HTTP diff download with pre-filtering:
  - Review URL building in `_build_diff_url()` - must handle GitHub.com vs Enterprise correctly
  - Check `_fetch_and_parse_diff_with_prefiltering()` - streaming with httpx.AsyncClient, 16KB chunks
  - Verify pre-filtering happens BEFORE parsing (binary detection, exclude patterns)
  - Ensure automatic fallback to API methods if HTTP fetch fails
  - Review `FilteringStreamingDiffParser` usage - proper chunk handling and finalization
  - Check statistics logging - bytes processed/skipped, filter ratio, MB metrics
  - Verify early stopping when `max_files` limit is reached during streaming
  - SSL context handling for self-hosted instances (GitLab)

- **[Review Synthesis Logic]** - Two-phase review system (v1.15.0+):
  - Phase 1 fetches and synthesizes previous comments with fast model
  - Verify bot comment filtering (`get_authenticated_username()` comparison)
  - Check synthesis is skipped when no comments exist
  - Ensure synthesis output is displayed for transparency
  - Review token limits for synthesis (default 2000 tokens max)

- **[Adaptive Context Windows]** - Dynamic sizing based on content:
  - Review `get_adaptive_context_size()` logic in providers
  - Verify auto-activation of big-diffs mode (>60K chars)
  - Check manual `--big-diffs` flag is respected
  - Ensure context window sizes are appropriate per model
  - Review token estimation calculations (chars to tokens ratio)

- **[Skip Review Logic]** - Multiple skip conditions:
  - Keyword matching in title/description (`[skip ai-review]`, etc.)
  - Bot author detection (renovate, dependabot, etc.)
  - Dependency update patterns (regex matching)
  - Documentation-only changes (file extension/path checks)
  - Draft PR/MR detection
  - Review that all skip reasons return proper exit code 0

## Common Pitfalls & Anti-Patterns

*   **❌ Using `default_factory` with field references** (commit `8fbf91b`):
    *   **Problem**: `default_factory` executes at field definition, not instance creation
    *   **Impact**: Breaks layered config - provider/model mismatches
    *   **Solution**: Use `None` default + getter method pattern
    *   **Example**: `ai_model: str | None = None` with `def get_ai_model(self) -> str`

*   **❌ Introducing aiohttp when httpx is sufficient**:
    *   **Problem**: Adds unnecessary dependency and inconsistency
    *   **Impact**: More code to maintain, test complexity increases, dual HTTP libraries
    *   **Solution**: Use `httpx` for both sync and async HTTP operations
    *   **httpx capabilities**: Sync requests, async requests, streaming, SSL contexts, timeouts

*   **❌ Blocking I/O in async hot paths**:
    *   Using synchronous `open()`, `requests`, or `.invoke()` in async handlers degrades performance
    *   **Acceptable**: Startup/initialization operations (config loading, one-time health checks)
    *   **Not acceptable**: Inside async loops, repeated API calls, request handlers
    *   Wrap blocking operations with `asyncio.to_thread()` if necessary

*   **❌ Improper `httpx.AsyncClient` usage**:
    *   Creating new `httpx.AsyncClient` for each request wastes resources
    *   **Correct**: Reuse client across multiple requests within async context manager
    *   For streaming: Create client with timeout, use `client.stream()` method

*   **❌ Missing `await` keywords**:
    *   Forgetting to `await` coroutines leads to runtime warnings or incorrect behavior
    *   Pay attention to `await` in: `httpx` async requests, `langchain` `.ainvoke()`, `aiofiles` operations
    *   Test async code with `@pytest.mark.asyncio`

*   **❌ Hardcoded secrets**:
    *   API keys embedded in code are security risks
    *   **Correct**: Use environment variables via `pydantic-settings.BaseSettings`
    *   Never log sensitive data - use structured logging with field filtering

*   **❌ Breaking configuration priority**:
    *   Validators that set defaults bypass CLI/env overrides
    *   **Correct**: Validators should only validate, not set values
    *   Test with: `Config(field=value)` to ensure value is respected

*   **❌ Ignoring structured output**:
    *   Manually parsing LLM JSON/string outputs is error-prone
    *   **Correct**: Use LangChain's `PydanticOutputParser` or `model.with_structured_output()`
    *   For this project: Most output is markdown (free-form), synthesis produces strings

---
<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->

## Architecture & Design Decisions

### HTTP Client Library: httpx (Standard)

**Decision**: Use `httpx` as the standard HTTP client library (both sync and async operations)

**Rationale**:
- **Single dependency**: `httpx` provides both synchronous (`httpx.get()`) and asynchronous (`httpx.AsyncClient()`) APIs
- **Simplicity**: Intuitive API for both simple and complex HTTP operations
- **Streaming support**: Full async streaming with `client.stream()` and `response.aiter_bytes()`
- **SSL context support**: Accepts `ssl.SSLContext` objects via `verify` parameter
- **Used throughout**: Health checks, context loading, diff streaming

**Capabilities**:
- ✅ Synchronous requests: `httpx.get()`, `httpx.post()`
- ✅ Async requests: `httpx.AsyncClient().get()`
- ✅ Streaming: `async with client.stream('GET', url) as response:`
- ✅ SSL contexts: `AsyncClient(verify=ssl_context)`
- ✅ Timeouts: `AsyncClient(timeout=httpx.Timeout(seconds))`

**Example locations**:
- `src/ai_code_review/providers/ollama.py`: Health checks using `httpx.get()` and `httpx.AsyncClient()`
- `src/ai_code_review/core/github_client.py`: Streaming diff downloads with `httpx.AsyncClient`
- `src/ai_code_review/core/gitlab_client.py`: Streaming diff downloads with SSL context support

**Legacy Exception**:
- `src/ai_code_review/utils/ssl_utils.py`: SSL certificate downloads using `aiohttp` (legacy code, not migrated due to specific error handling dependencies)

### Configuration System: Layered Priority

**Priority Order**: `CLI args > Environment variables > Config file > Field defaults`

**Critical Pattern for Interdependent Fields** (see commit `8fbf91b`):

❌ **NEVER use `default_factory` with field references**:
```python
# WRONG - breaks layered config
ai_model: str = Field(
    default_factory=lambda: get_default_model_for_provider(DEFAULT_AI_PROVIDER)
)
```

✅ **Use None + getter pattern**:
```python
# CORRECT - resolves at access time
ai_model: str | None = Field(default=None)

def get_ai_model(self) -> str:
    if self.ai_model:
        return self.ai_model
    return get_default_model_for_provider(self.ai_provider)
```

**Why**: `default_factory` executes at field definition time, NOT at instance creation. It cannot access other field values dynamically.

**Application**: All code must use `config.get_ai_model()` instead of `config.ai_model` to respect the computed default.

### Review Context System (v1.15.0+)

**Two-Phase Review with Comment Synthesis**:

1. **Phase 1 (Synthesis)**: 
   - Fetches up to 30 recent comments/reviews from platform API
   - Uses fast model (Gemini Flash, Claude Haiku) to synthesize key insights
   - Filters bot comments and system notes
   - Generates concise summary (~2000 tokens max)

2. **Phase 2 (Main Review)**:
   - Receives synthesis as additional context
   - Generates review aware of previous discussions
   - Automatically skips synthesis when no comments exist

**Configuration**:
- `enable_review_context`: Enable fetching previous reviews (default: true)
- `enable_review_synthesis`: Enable LLM synthesis preprocessing (default: true)
- `synthesis_model`: Fast model for synthesis (auto-selected if None)
- `max_comments_to_fetch`: Limit for API calls (default: 30)

### Team/Organization Context (v1.15.0+)

**Hierarchical Context Loading**:

Priority: `team_context_file > project_context_file > commit_history`

**Features**:
- Supports local file paths and HTTP/HTTPS URLs
- Remote URLs fetch content at runtime (no caching)
- Configuration via CLI (`--team-context`), env var (`TEAM_CONTEXT_FILE`), or YAML config
- Used for organization-wide coding standards shared across projects

**Implementation**: Synchronous `httpx` for remote loading is acceptable - this happens once at startup and is not performance-critical.

## Business Logic & Implementation Decisions

- **Long-running LLM calls**: Response times of 30+ seconds are normal and expected in this domain
- **Retry logic**: `review_engine.py` handles API provider failures and rate limiting automatically
- **Dry-run mode**: Intentional throughout codebase for cost-free testing during development
- **Multiple AI providers**: Enables fallback when one service is unavailable
- **Adaptive context windows**: Automatically adjusts based on diff size (see `get_adaptive_context_size()`)
- **Blocking I/O at startup**: Acceptable for initialization operations (config loading, health checks)
- **Model selection**: Gemini 3 Pro Preview (v1.15.0+) for main reviews, Flash/Haiku for synthesis

## Recent Major Features (since v1.12.0)

### v1.17.0 - Complete Diff Fetching System
- HTTP `.diff` endpoint fetching for GitLab and GitHub (all files included)
- Streaming diff parser with 16KB chunk processing (`FilteringStreamingDiffParser`)
- Intelligent pre-filtering: skip binary files and excluded patterns before parsing
- Automatic transparent fallback to platform API if HTTP method fails
- Enhanced local Git client with pre-filtering for binary and excluded files
- Configurable download timeout (`diff_download_timeout`, default: 120s)
- Detailed statistics logging (MB processed/skipped, filter ratio)

### v1.15.0 - Review Context & Gemini 3
- Intelligent review context with comment synthesis (two-phase system)
- Upgraded to Gemini 3 Pro Preview as default model
- Team/organization context support with remote URL loading
- Synthesis model auto-selection per provider

### v1.13.0 - Context Generator Enhancements  
- CI/CD documentation integration for context files
- Context7 library integration for external documentation
- Improved symlink handling in project structure
- Better library selection and separation from CI docs

### v1.12.1 - Configuration & Packaging
- Fixed layered configuration with None + getter pattern (commit `8fbf91b`)
- Dry-run mode improvements for context generator
- Package renamed to `ai-code-review-cli` on PyPI
- Container support for local Git reviews

## Domain-Specific Context

- **GitLab Integration**: Supports both GitLab.com and self-hosted instances via custom base URLs
- **GitHub Integration**: Full PR support with API v3 integration
- **Local Git Mode**: Direct diff analysis without platform APIs (requires Git in container)
- **AI Provider APIs**: Each provider (Anthropic, Gemini, Ollama) has different auth and rate limiting patterns
- **Token Management**: Cost optimization through adaptive context windows - longer contexts acceptable for better review quality
- **Review Formats**: Output must be markdown-compatible for GitLab/GitHub display
- **Comment Synthesis**: Uses fast models to reduce token costs while maintaining context awareness

## Special Cases & Edge Handling

- **SSL verification**: Can be disabled for self-hosted GitLab instances (`--disable-ssl-verify`)
- **API key security**: `GITLAB_TOKEN` and other API keys should never appear in logs (use `mask_sensitive_data()`)
- **Empty commits**: Draft MRs and empty commits are intentionally skipped without error
- **Directory structure**: The `.ai_review/` directory must be preserved for context file functionality
- **Configuration priority**: CLI args > Environment variables > Config files > Field defaults
- **Interdependent fields**: Never use `default_factory` - use None + getter pattern instead
- **HTTP operations**: Use `httpx` exclusively for all HTTP operations (sync and async) - no aiohttp
- **Context loading**: Remote URL fetching happens at startup (not cached) - synchronous is acceptable
- **Comment filtering**: System notes, bot comments, and non-author responses filtered from synthesis