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
- **langchain>=0.2.0** - Core dependency for building applications with Large Language Models (LLMs). Reviewers must understand LangChain concepts like chains, agents, and model integrations (Google GenAI, Anthropic, Ollama are also present).
- **click>=8.1.0** - Defines the application's Command-Line Interface structure. Code changes will often involve creating or modifying `@click.command()` or `@click.option()` decorators.
- **aiohttp>=3.9.0** - Used for making asynchronous HTTP requests. Reviewers should focus on correct `async/await` patterns, client session management, and handling of network errors.
- **python-gitlab>=4.0.0** & **pygithub>=2.1.0** - Indicates direct interaction with GitLab and GitHub APIs. Code review should verify correct API usage, authentication, and handling of platform-specific data structures.
- **pydantic>=2.5.0** - Used for data validation and settings management. Reviewers should check for well-defined data models, proper type enforcement, and validation logic.
- **structlog>=23.2.0** - Implements structured logging. Reviewers should ensure logs are consistent, contain relevant context, and avoid leaking sensitive information.

### Development Tools & CI/CD
- **Testing:** `pytest>=7.4.0` with `pytest-asyncio` for testing asynchronous code and `pytest-cov` for coverage reporting.
- **Code Quality:** `ruff>=0.1.0` for linting and formatting, and `mypy>=1.7.0` for static type checking.
- **Build/Package:** Modern Python packaging using `pyproject.toml`.
- **CI/CD:** GitLab CI/CD, configured via `.gitlab-ci.yml`.

## Architecture & Code Organization

### Project Organization
```
.
├── .ai_review/
│   └── project.md
├── docs/
│   ├── context-generator.md
│   ├── developer-guide.md
│   └── user-guide.md
├── src/
│   ├── ai_code_review/
│   │   ├── core/
│   │   ├── models/
│   │   ├── providers/
│   │   ├── utils/
│   │   ├── __init__.py
│   │   └── cli.py
│   └── context_generator/
│       ├── core/
│       ├── sections/
│       ├── templates/
│       ├── utils/
│       ├── __init__.py
│       ├── cli.py
│       ├── constants.py
│       └── models.py
├── tests/
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_context_generator_simple.py
│   ├── unit/
│   │   ├── test_anthropic_provider.py
│   │   ├── test_base_provider.py
│   │   ├── test_cli.py
│   │   ├── test_cli_ci.py
│   │   ├── test_config.py
│   │   ├── test_config_file_loading.py
│   │   ├── test_context_generator_base.py
│   │   ├── test_context_generator_cli.py
│   │   ├── test_context_generator_code_extractor.py
│   │   ├── test_context_generator_constants.py
│   │   ├── test_context_generator_context_builder.py
│   │   └── test_context_generator_facts_extractor.py
│   ├── __init__.py
│   └── conftest.py
├── .gitignore
├── .gitlab-ci.yml
├── .pre-commit-config.yaml
├── Containerfile
├── README.md
└── pyproject.toml
```

### Architecture Patterns
**Code Organization:** Layered Architecture. The application is structured into distinct layers: a Command Line Interface (`cli.py`) for user interaction, a `core` layer (`review_engine.py`) for orchestrating business logic, a `providers` layer for interacting with external AI and platform APIs, and a `models` layer (`config.py`) for data structures and configuration.
**Key Components:**
- **`ReviewEngine`:** The central orchestrator in `src/ai_code_review/core/review_engine.py`. It initializes platform clients (e.g., GitLab, GitHub) and AI providers based on the configuration, and manages the end-to-end process of fetching code, generating a review, and posting it.
- **Pydantic Models:** Used extensively in `src/ai_code_review/models/config.py` and `src/context_generator/models.py`. `pydantic.BaseSettings` is used for application configuration, providing type validation and loading from environment variables. `pydantic.BaseModel` is used for data structures throughout the application.
- **Provider Abstraction:** The system uses a factory pattern (`_create_platform_client`, `_create_ai_provider` in `ReviewEngine`) and interfaces (`PlatformClientInterface`, `BaseAIProvider`) to decouple the core logic from specific implementations of AI services (Ollama) and code platforms (GitLab, GitHub).
**Entry Points:** The application is a command-line tool. The main entry point is defined in `src/ai_code_review/cli.py` using the `click` library. It parses arguments, loads the `Config` object, and instantiates and runs the `ReviewEngine`.

### Important Files for Review Context
- **`src/ai_code_review/cli.py`** - This is the main entry point. Understanding this file is crucial for seeing how user inputs are processed, how configuration is loaded, and how the core `ReviewEngine` is invoked.
- **`src/ai_code_review/models/config.py`** - Defines all application settings using Pydantic. Nearly all components depend on this configuration. Reviewers must be familiar with this file to understand how features are enabled/disabled and how the application is configured.
- **`src/ai_code_review/core/review_engine.py`** - Contains the primary business logic. It connects the platform client (e.g., GitLab) to the AI provider. Changes here directly impact the core functionality of generating and posting code reviews.

### Development Conventions
- **Naming:** Classes use `PascalCase` (e.g., `ReviewEngine`, `ContextResult`). Functions, methods, and variables use `snake_case` (e.g., `_resolve_project_params`). Internal helper functions are prefixed with a single underscore (`_get_enum_value`). Constants are `UPPER_SNAKE_CASE` (e.g., `AUTO_BIG_DIFFS_THRESHOLD_CHARS`).
- **Module Structure:** The project follows a `src` layout. Code is organized into feature-based packages (`ai_code_review`, `context_generator`). Within these, modules are separated by responsibility (`core`, `models`, `providers`, `utils`), promoting a clear separation of concerns.
- **Configuration:** Configuration is centralized in `src/ai_code_review/models/config.py` using `pydantic_settings.BaseSettings`. This provides strongly-typed, validated configuration that can be loaded from environment variables.
- **Testing:** The `tests/` directory is structured with separate `unit/` and `integration/` subdirectories, indicating a clear distinction between testing components in isolation and testing their interactions. The presence of `conftest.py` implies the use of `pytest` and its fixture system.

## Code Review Focus Areas

- **[Asynchronous API Integration]** - The project uses `aiohttp` and `httpx` for platform interactions. Review for correct `async`/`await` usage in platform clients (e.g., `GitLabClient`, `GitHubClient`). Ensure I/O-bound calls to external APIs are non-blocking and that `ClientSession` objects are managed properly to avoid resource leaks.

- **[Provider Abstraction and Factory Pattern]** - The `ReviewEngine` uses factory methods (`_create_platform_client`, `_create_ai_provider`) to instantiate clients based on an interface (`PlatformClientInterface`). When a new provider is added, verify that it correctly implements the required interface and that the factory logic in `ReviewEngine` is updated. Ensure no provider-specific logic leaks into the main orchestration loop.

- **[LangChain Prompt and Chain Management]** - The core AI logic is encapsulated in LangChain chains (e.g., `create_review_chain`). Scrutinize changes to prompt templates in `utils/prompts.py`. Verify that the chain construction correctly handles context formatting, model parameters, and output parsing, especially for different AI providers which may have unique requirements.

- **[Pydantic Configuration and Validation]** - Configuration is managed via `pydantic` and `pydantic-settings` with custom validators (`field_validator`, `model_validator`). When new settings are added to `models/config.py`, check that they have strict type hints and robust validation logic to prevent misconfiguration. Ensure environment variable overrides and default values are handled as expected.

- **[Custom Exception Handling and Exit Codes]** - The application defines specific exceptions like `ReviewSkippedError` and `PlatformAPIError` which map to exit codes in `cli.py`. Review changes to ensure that these custom exceptions are raised in the correct business logic paths (e.g., when a diff is too large) and are caught at the entry point to provide clear user feedback and the correct exit code.

## Library Documentation & Best Practices

### 1. API Usage Patterns

*   **aiohttp (Client):** HTTP requests must be made using an `aiohttp.ClientSession` instance, preferably within an `async with` block to ensure proper connection pooling and resource cleanup. Use `session.get()` for GET and `session.post()` for POST requests, awaiting the response methods like `resp.text()`.
    ```python
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            content = await resp.text()
    ```
*   **aiohttp (Server):** Applications should be defined by creating a `web.Application` instance, adding routes via `app.add_routes([...])`, and running the server with `web.run_app(app)`. For finer control over the application lifecycle, use `web.AppRunner` and `web.TCPSite`.
*   **langchain:**
    *   **Chaining:** The primary pattern for building logic is the LangChain Expression Language (LCEL) using the pipe (`|`) operator. Chains should be composed of `PromptTemplate`, a model object, and an `OutputParser`.
        ```python
        chain = prompt | model | output_parser
        ```
    *   **Model Invocation:** Use `.ainvoke()` and `.astream()` for non-blocking calls within an `aiohttp` server.
    *   **RAG:** The standard pattern is to load documents, split them with a `TextSplitter`, create embeddings, store them in a vector store, and use `vectorstore.as_retriever()` to fetch context.
    *   **Agents & Tools:** Tools should be defined as functions with the `@tool` decorator or as Pydantic `BaseModel` classes. These are then passed to an agent created with `create_tool_calling_agent`.
*   **pydantic:** Data structures should be defined by inheriting from `pydantic.BaseModel`. This is the standard for data validation, serialization, and defining structured outputs for LangChain.
*   **aiofiles:** All file I/O must be performed using `aiofiles.open` within an `async with` block. File operations like `read` and `write` are coroutines and must be awaited. Asynchronous filesystem operations (e.g., `rename`, `remove`) should use the `aiofiles.os` module.
    ```python
    async with aiofiles.open('filename', mode='r') as f:
        contents = await f.read()
    ```
*   **httpx:** The provided documentation is for a Go-based command-line tool for web reconnaissance, not the Python `httpx` library. It is not applicable for a Python package making HTTP requests. The project should use `aiohttp` for this purpose as per its documentation.

### 2. Best Practices

*   **Asynchronous Operations:** In `aiohttp` handlers, always use the `async` versions of library calls to avoid blocking the event loop. This includes `langchain`'s `.ainvoke()` and `.astream()` methods and all `aiofiles` functions. Standard synchronous file I/O (`open()`) or network calls must be avoided.
*   **Resource Management:** Use `async with` statements for `aiohttp.ClientSession` and `aiofiles.open` to ensure resources like connection pools and file handles are managed automatically and safely.
*   **API Key Management:** LangChain API keys should be loaded from environment variables (`os.environ.get(...)`) and never hardcoded in the source code.
*   **Data Validation:** Use Pydantic models to define and validate the structure of API request bodies and responses in the `aiohttp` application. This ensures type safety and clear API contracts.
*   **Testing:**
    *   `aiohttp` endpoints should be tested using `aiohttp.test_utils.TestClient`.
    *   Code using `aiofiles` should be tested by mocking `aiofiles.threadpool.sync_open` as demonstrated in the documentation.
*   **LangChain Caching:** To improve performance and reduce costs, enable LLM caching using `langchain.globals.set_llm_cache` with either `InMemoryCache` or a persistent `SQLiteCache`.

### 3. Common Pitfalls

*   **Blocking I/O:** Using standard `open()`, `requests`, or synchronous LangChain methods (`.invoke()`) inside an `async def` function in `aiohttp`. This will block the entire server's event loop and severely degrade performance.
*   **Improper `ClientSession` Usage:** Creating a new `aiohttp.ClientSession` for each request is inefficient. A single session should be created and reused across multiple requests.
*   **Missing `await`:** Forgetting to `await` coroutines from `aiohttp`, `langchain`, or `aiofiles` will lead to runtime errors or incorrect behavior.
*   **Hardcoded Secrets:** Embedding API keys directly in the code instead of using environment variables is a major security risk.
*   **Ignoring Structured Output:** Manually parsing JSON or string outputs from LLMs is error-prone. Use LangChain's `PydanticOutputParser` or `model.with_structured_output()` for reliable, validated data structures.

### 4. Integration Recommendations

*   **API Layer (`aiohttp` + `pydantic`):** `aiohttp` should serve the web API. Request handlers should use Pydantic models to parse and validate incoming JSON bodies. Pydantic models should also be used to serialize response data, creating a well-defined API.
*   **Core Logic (`langchain`):** The `aiohttp` handlers will call LangChain components (chains, agents) to execute the core business logic. All calls into LangChain from the API layer must use async methods (e.g., `chain.ainvoke(...)`).
*   **Filesystem (`aiofiles`):** If an API endpoint needs to read from or write to a file (e.g., processing an upload, logging to a file), it must use `aiofiles` to prevent blocking.
*   **Tools (`langchain` + `pydantic`):** When building LangChain agents, Pydantic models are the recommended way to define the schema for tools. This provides robust input validation for tool calls initiated by the agent.

### 5. Configuration Guidelines

*   **Development Environment:** The `aiohttp-debugtoolbar` can be enabled during development for easier debugging via `aiohttp_debugtoolbar.setup(app)`. This should not be enabled in production.
*   **Type Checking:** To ensure correct static analysis of Pydantic models, the Mypy plugin must be enabled in `pyproject.toml` or `mypy.ini`:
    ```toml
    [tool.mypy]
    plugins = ["pydantic.mypy"]
    ```
*   **Tracing and Debugging:** For observability into LangChain executions, configure LangSmith by setting the `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT` environment variables.
*   **Installation:** The project should install specific versions of libraries. For Pydantic, if a specific major version is required (e.g., V1 for compatibility), it should be pinned as `"pydantic==1.*"`. Otherwise, `pydantic` will install V2.

---
<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->

### Business Logic & Implementation Decisions

- Long-running LLM calls are acceptable and expected in this domain - response times of 30+ seconds are normal
- Retry logic in `review_engine.py` handles API provider failures and rate limiting
- The `dry_run` mode throughout the codebase is intentional for cost-free testing during development
- Multiple AI provider support allows fallback when one service is unavailable

### Domain-Specific Context

- **GitLab Integration**: Supports both GitLab.com and self-hosted GitLab instances via custom base URLs
- **AI Provider APIs**: Each provider (Anthropic, Gemini, Ollama) has different authentication and rate limiting patterns
- **Token Management**: Cost optimization through adaptive context windows - longer contexts are acceptable for better review quality
- **Review Formats**: Output must be markdown-compatible for GitLab/GitHub display

### Special Cases & Edge Handling

- SSL verification can be disabled for self-hosted GitLab instances (`--disable-ssl-verify`)
- `GITLAB_TOKEN` and other API keys should never appear in logs (use `mask_sensitive_data()`)
- Empty commits and draft MRs are intentionally skipped without error
- The `.ai_review/` directory structure must be preserved for context file functionality
- Configuration layering: CLI args > Environment variables > Config files > Defaults