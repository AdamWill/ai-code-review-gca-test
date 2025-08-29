# Project Specifications: AI-Powered Code Review Tool

## 📋 Project Overview

AI-powered Python CLI tool that provides automated code review assistance for GitLab Merge Requests. The tool analyzes MR diffs using AI models and generates structured feedback to support human reviewers in identifying potential issues, security vulnerabilities, and code quality improvements.

### Core Functionality

**Code Analysis**: Fetches MR diffs from GitLab API and analyzes changes for logic issues, security concerns, performance problems, and architectural patterns. Focuses on high-level feedback that complements static analysis tools.

**Context Integration**: Optionally reads project documentation (README, coding standards, architecture docs) to provide contextually relevant reviews that align with project-specific practices and conventions.

**Structured Output**: Generates collapsible markdown reviews with file-by-file analysis, actionable suggestions, and executive summaries suitable for both technical and non-technical stakeholders.

### Usage Model

The tool integrates into GitLab CI/CD pipelines as an additional job that runs automatically on merge request events. It fetches the MR diff, processes it through the configured AI provider, and posts the review as a comment on the MR. This provides immediate feedback to assist human reviewers without replacing the human review process.

### Technical Implementation

Built with Python 3.12+, LangChain for AI provider abstraction, and modern development tooling (uv, ruff, mypy). Supports local development with Ollama and production deployment with cloud AI providers (Gemini default) in containerized environments.

## 🎯 Functional Requirements

### Core Features

**FR-001: GitLab Integration**
- Fetch MR diffs from GitLab API using project ID and MR IID
- Support both numeric project IDs and URL-encoded paths (e.g., `group/subgroup/project`)
- Handle authentication via GitLab Personal Access Token
- Support configurable GitLab instance URLs

**FR-002: AI Code Review**
- Generate comprehensive code reviews using AI models
- Focus on high-level feedback: logic, correctness, security, performance, architecture
- Ignore trivial formatting/linting issues
- Provide actionable suggestions with code snippets
- Support multiple AI providers (Gemini primary, extensible architecture)

**FR-003: MR Summary Generation**
- Generate concise, high-level summaries of merge requests
- Business-friendly format for non-technical stakeholders
- Include headline, key changes, and impact assessment

**FR-004: Output Flexibility**
- Print reviews to stdout for CLI workflows
- Post reviews directly as MR notes in GitLab
- Support both review-only and review+summary modes

**FR-005: Configuration Management**
- Environment variable configuration
- Command-line argument overrides
- Support for language hints and content limits
- Dry-run mode for testing without API calls

### Advanced Features

**FR-006: Multi-Provider AI Support**
- Local Development: Ollama with qwen2.5-coder:7b (local development only, cost-free)
- Production/Container Default: Google Gemini (gemini-2.5-pro)
- CI/CD: Cloud providers only (Gemini, OpenAI, Anthropic)
- Extensible architecture via LangChain for cloud providers
- Provider-specific configuration and error handling

**FR-007: Project Context Integration (Optional)**
- **Standard Context File**: `.ai_review/project.md` - project info, stack, architecture, style guides
- **Auto-discovery Mode**: Automatically find README.md, CLAUDE.md, .cursorrules, etc.
- **Custom Path Mode**: Specify custom path within repo via `--context-file` or env var
- **External URL Mode**: Fetch context from external URL (documentation sites)
- **CI/CD Configuration**: Environment variable `ENABLE_PROJECT_CONTEXT=true/false`
- **Token Management**: Smart truncation when context + diff exceeds token limits

**FR-008: Customizable Prompt Templates (Future)**
- Template override system via `.ai_review/templates/` directory
- Base template inheritance with custom extensions
- Configurable review focus areas and output formats
- Project-specific guidelines integration

**FR-009: Content Processing**
- Handle large diffs with intelligent truncation
- File count and character limits
- Context-aware content prioritization based on project context
- Diff parsing and formatting for AI consumption

**FR-010: Error Handling & Resilience**
- Comprehensive error handling for API failures with retry logic
- Graceful degradation on partial failures
- Detailed logging for troubleshooting
- CI/CD specific error handling with appropriate exit codes
- Timeout management for long-running operations
- Handling of edge cases (empty MRs, API rate limits, network issues)

## 🔧 Non-Functional Requirements

### Performance
- **NFR-001**: Process MRs with up to 100 files and 100,000 characters
- **NFR-002**: Complete review generation within 30 seconds for typical MRs
- **NFR-003**: Handle API rate limits gracefully with backoff strategies
- **NFR-004**: CI/CD job timeout protection (max 10 minutes with configurable timeout)
- **NFR-005**: Efficient caching to reduce repeated API calls and context loading
- **NFR-006**: Parallel processing where possible (context loading, API calls)

### Reliability
- **NFR-007**: 99% uptime for core functionality
- **NFR-008**: Fail gracefully on API errors without data loss
- **NFR-009**: Comprehensive logging for all operations

### Security
- **NFR-010**: Secure handling of API tokens and credentials (cloud providers only in containers)
- **NFR-011**: No logging of sensitive code content or API keys
- **NFR-012**: Support for enterprise GitLab instances with custom certificates
- **NFR-013**: Local development with Ollama requires no external API keys
- **NFR-014**: GitLab token with minimal required permissions (api scope for MR access)
- **NFR-015**: Use GitLab masked/protected variables for sensitive data
- **NFR-016**: Validate GitLab token permissions before processing
- **NFR-017**: Support for private repositories and restricted access

### Maintainability
- **NFR-018**: 90%+ test coverage on all critical paths
- **NFR-019**: Full type annotations using Python 3.12+ features
- **NFR-020**: Comprehensive documentation and examples
- **NFR-021**: Modular architecture for easy feature extension

### Usability
- **NFR-022**: Intuitive CLI interface following Unix conventions
- **NFR-023**: Clear error messages with actionable guidance
- **NFR-024**: Support for both local development (Ollama) and CI/CD usage (cloud providers)

## 🛠️ Technology Stack

### Core Technologies
- **Python**: 3.12+ (using latest features and performance improvements)
- **Package Manager**: `uv` (fast, modern Python package management)
- **Build System**: `hatchling` (modern, standards-compliant)

### Development Tools
- **Linting/Formatting**: `ruff` (fast, comprehensive)
- **Type Checking**: `mypy` (strict mode)
- **Testing**: `pytest` with fixtures and async support
- **Documentation**: `mkdocs` with material theme

### Dependencies
- **CLI Framework**: `click` (replacing argparse for better UX)
- **HTTP Client**: `aiohttp` (async HTTP for better performance)
- **GitLab API**: `python-gitlab` (mature GitLab integration)
- **LLM Framework**: `langchain` + `langchain-community` (prompt management, LLM abstraction)
- **AI Providers**: 
  - `ollama` (local development, primary for Phase 1)
  - `langchain-google-genai` (Gemini - production default)
  - `langchain-openai` (OpenAI - optional)
  - `langchain-anthropic` (Claude - optional)
- **Configuration**: `pydantic` v2+ (validation and settings)
- **Logging**: `structlog` (structured logging)

### Development Infrastructure
- **Containerization**: `podman` with UBI9 base image (AMD64, cloud providers only)
- **Container Registry**: GitLab Container Registry with Buildah
- **CI/CD**: GitLab CI with cloud provider integration (Gemini default)
- **Version Control**: Git with conventional commits
- **Local Development**: Ollama for cost-free development and testing

### Container Specifications
- **Base Image**: Red Hat UBI9 (ubi9/ubi:latest)
- **Architecture**: AMD64 only
- **Build Tool**: Buildah in GitLab CI
- **Registry**: GitLab Container Registry (`$CI_REGISTRY_IMAGE`)
- **Security**: Non-root user, minimal dependencies
- **Size Target**: <500MB final image

## 🎭 AI Prompts and LangChain Templates

### System Prompt for Code Review (LangChain Template)
```python
from langchain.prompts import SystemMessagePromptTemplate

system_template = """
You are an expert senior software engineer and a meticulous code reviewer. 
Your goal is to provide concise, high-quality, constructive feedback on merge requests to help developers improve their code. 
You need to focus on review ONLY the changes in the diff, not the entire codebase. 
Your tone should be helpful, collaborative, and professional. 
You must adhere strictly to the response format requested in the user's prompt.

Model Context: You are running on {model_name} via {provider_name}.
"""

system_prompt = SystemMessagePromptTemplate.from_template(system_template)
```

### Code Review User Prompt Template (LangChain)
```python
from langchain.prompts import HumanMessagePromptTemplate

review_template = """
Please review the following code changes from a merge request.

{language_hint_section}

{project_context_section}

## Guidelines

- **Focus on High-Level Feedback:** Concentrate on logic, correctness, security vulnerabilities, performance bottlenecks, architectural patterns, and readability.
- **Ignore Trivial Issues:** Do not comment on minor stylistic issues, formatting, or things a linter would automatically catch.
- **Be Actionable:** Provide clear, concise, and actionable suggestions. Explain *why* a change is recommended.
- **Provide Code Snippets:** When suggesting a change, include a small code snippet to illustrate your point.

## Response Format

Structure your feedback in Markdown using collapsible sections as follows:

---

### General Feedback

A brief, high-level overview of the merge request. Mention the overall quality and any major architectural points.

### 📂 File Reviews

For each file with significant feedback, use this collapsible format:

<details>
<summary><strong>📄 `path/to/file.ext`</strong> - Brief summary of main issues</summary>

#### Reviews
- **[Issue Type]** Brief description of the issue or suggestion
  - **Reasoning:** Detailed explanation of why this is important
  - **Suggestion:** Specific actionable recommendation
  
```language
// Code example if applicable
suggested_improvement();
```

#### Questions (if any)
- **[Question]** Clarifying question about specific implementation. ONLY if necessary

#### Additional Comments (if any)
- **[Note]** Any additional observations or recommendations. ONLY if necessary

</details>

### ✅ Summary

- **Overall Assessment:** Quality rating and key recommendations
- **Priority Issues:** Most critical items to address
- **Minor Suggestions:** Optional improvements

---

## Code Diff

```diff
{diff_content}
```
"""

review_prompt = HumanMessagePromptTemplate.from_template(review_template)
```

### MR Summary User Prompt Template (LangChain)
```python
from langchain.prompts import HumanMessagePromptTemplate

summary_template = """
Based on the code diff below, please provide a concise, high-level summary of the merge request. The summary should be easy for a project manager or a new team member to understand.

{project_context_section}

## Response Format

Use this collapsible markdown format:

<details>
<summary><strong>📋 MR Summary</strong> - Single sentence describing the main change</summary>

### Key Changes
- Brief bullet point of most important change
- Another significant modification
- Additional relevant change

### Impact Assessment
- **Modules Affected:** List of impacted components
- **User Impact:** Description of user-facing changes (if any)
- **Technical Impact:** Infrastructure or architectural changes

### Risk Level
- **Low/Medium/High** - Brief justification

</details>

## Code Diff

```diff
{diff_content}
```
"""

summary_prompt = HumanMessagePromptTemplate.from_template(summary_template)
```

### LangChain Chain Examples
```python
from langchain.chains import LLMChain
from langchain.schema import StrOutputParser

# Code Review Chain
review_chain = (
    {
        "diff_content": lambda x: x["diff"], 
        "language_hint_section": lambda x: f"**Primary Language:** `{x['language']}`" if x.get('language') else "",
        "project_context_section": lambda x: f"## Project Context\n\n{x['context']}" if x.get('context') else ""
    }
    | review_prompt
    | llm
    | StrOutputParser()
)

# Summary Chain
summary_chain = (
    {
        "diff_content": lambda x: x["diff"],
        "project_context_section": lambda x: f"## Project Context\n\n{x['context']}" if x.get('context') else ""
    }
    | summary_prompt
    | llm
    | StrOutputParser()
)
```

### Example Output Format

#### Code Review Example
```markdown
### General Feedback

This MR introduces user authentication functionality with proper security measures. The implementation follows good practices with JWT tokens and password hashing.

### 📂 File Reviews

<details>
<summary><strong>📄 `src/auth/login.py`</strong> - Security improvements needed</summary>

#### Reviews
- **[Security]** Password validation could be strengthened
  - **Reasoning:** Current regex allows weak passwords that could be easily compromised
  - **Suggestion:** Implement minimum 12 characters with mixed case, numbers, and symbols
  
```python
# Consider using a more robust password validator
from django.contrib.auth.password_validation import validate_password
validate_password(password, user)
```

#### Questions
- **[Question]** Should we implement rate limiting for login attempts?

</details>

<details>
<summary><strong>📄 `src/auth/models.py`</strong> - Minor optimizations</summary>

#### Reviews
- **[Performance]** Database index missing on email field
  - **Reasoning:** Email lookups will be frequent and should be optimized
  - **Suggestion:** Add `db_index=True` to email field

</details>

### ✅ Summary

- **Overall Assessment:** Good implementation with security best practices
- **Priority Issues:** Strengthen password validation, add database indices
- **Minor Suggestions:** Consider rate limiting, add more comprehensive tests
```

#### MR Summary Example
```markdown
<details>
<summary><strong>📋 MR Summary</strong> - Implement user authentication system with JWT tokens</summary>

### Key Changes
- Add user login/logout endpoints with JWT authentication
- Implement password hashing using bcrypt
- Create user registration flow with email verification
- Add authentication middleware for protected routes

### Impact Assessment
- **Modules Affected:** Authentication, User management, API middleware
- **User Impact:** New login/registration functionality for end users
- **Technical Impact:** New database tables, authentication middleware integration

### Risk Level
- **Medium** - Core authentication changes require thorough testing

</details>
```

## 🏗️ Architecture Design

### Project Structure
```
ai-code-review/
├── src/ai_code_review/
│   ├── __init__.py
│   ├── cli.py                 # CLI entry point
│   ├── models/                # Pydantic models
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration models
│   │   ├── gitlab.py          # GitLab data models
│   │   └── review.py          # Review data models
│   ├── core/                  # Core business logic
│   │   ├── __init__.py
│   │   ├── gitlab_client.py   # GitLab API client
│   │   ├── ai_client.py       # AI provider abstraction
│   │   ├── review_engine.py   # Review orchestration
│   │   └── diff_processor.py  # Diff parsing and processing
│   ├── providers/             # AI provider implementations via LangChain
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract base provider using LangChain
│   │   ├── ollama.py          # Ollama local LLM implementation
│   │   ├── gemini.py          # Gemini implementation via langchain-google-genai
│   │   ├── openai.py          # OpenAI implementation via langchain-openai
│   │   └── anthropic.py       # Anthropic implementation via langchain-anthropic
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       ├── logging.py         # Logging configuration
│       ├── prompts.py         # LangChain prompt templates and chains
│       ├── context.py         # Project context handling and discovery
│       └── exceptions.py      # Custom exceptions
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── pyproject.toml
├── uv.lock
└── README.md
```

### Key Components

**Configuration Management**
- Pydantic models for type-safe configuration
- Environment variable loading with validation
- CLI argument parsing and merging
- Support for config files (TOML/YAML)

**GitLab Integration**
- Async HTTP client for GitLab API
- Robust error handling and retry logic
- Support for multiple GitLab instances
- Efficient diff fetching and processing

**AI Provider Abstraction via LangChain**
- LangChain-based unified interface for all AI providers
- Consistent prompt management using LangChain templates
- Provider-specific configuration through LangChain integrations
- Easy addition of new providers through LangChain ecosystem
- Built-in retry logic and error handling from LangChain

**Review Engine**
- Orchestrates the review process using LangChain chains
- LangChain prompt templates for code review and summary
- Project context integration with smart token management
- Template customization and inheritance system
- Output parsers for structured review formatting
- Async LangChain operations for better performance

**Project Context Handler**
- Auto-discovery of standard files (README.md, CLAUDE.md, .cursorrules)
- Standard context file support (`.ai_review/project.md`)
- External URL context fetching with caching
- Context size management and intelligent truncation
- Context priority system (custom > standard > auto-discovered)

## 🧪 Testing Strategy

### Unit Tests (90% coverage target)
- All core business logic functions
- Configuration validation
- Prompt template rendering
- Error handling scenarios
- Mock all external dependencies (GitLab API, AI APIs)

### Integration Tests
- End-to-end CLI workflows (local with Ollama, CI with cloud providers)
- GitLab API integration (with test instance)
- Ollama local LLM integration (local development only)
- LangChain cloud provider integration (Gemini, OpenAI, Anthropic)
- Container-based testing with cloud providers only

### Test Tools and Fixtures
- `pytest` with async support
- `pytest-mock` for mocking
- `pytest-asyncio` for async testing
- `pytest-cov` for coverage reporting
- Comprehensive test fixtures for common scenarios

## 🔧 Configuration Schema

### Environment Variables
```bash
# Required
GITLAB_TOKEN=glpat_xxxxxxxxxxxx

# AI Configuration (provider-specific)
AI_PROVIDER=ollama                      # ollama (local only), gemini (production), openai, anthropic
AI_MODEL=qwen2.5-coder:7b               # Model name for selected provider
AI_API_KEY=xxxxxxxxxxxx                 # Required for cloud providers (not ollama)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama server URL (local development only)

# Project Context (optional)
ENABLE_PROJECT_CONTEXT=true             # Enable/disable project context injection
PROJECT_CONTEXT_FILE=.ai_review/project.md  # Custom context file path
PROJECT_CONTEXT_URL=                    # External URL for project context (optional)
ENABLE_AUTO_DISCOVERY=true              # Auto-discover README, CLAUDE.md, .cursorrules

# GitLab CI/CD (automatic variables)
CI_PROJECT_PATH=                        # Automatically set by GitLab CI (project path)
CI_MERGE_REQUEST_IID=                   # Automatically set by GitLab CI (MR IID)
CI_SERVER_URL=                          # Automatically set by GitLab CI (GitLab instance URL)

# CI/CD Configuration
CI_JOB_TIMEOUT=1800                     # Maximum job runtime in seconds (30 min)
API_RETRY_COUNT=3                       # Number of retries for API failures
API_RETRY_DELAY=5                       # Delay between retries in seconds
ENABLE_CACHE=true                       # Enable caching for context files and responses

# Optional
GITLAB_URL=https://gitlab.com           # Fallback if CI_SERVER_URL not available
CODE_LANGUAGE_HINT=python
REVIEW_MAX_CHARS=100000
REVIEW_MAX_FILES=100
LOG_LEVEL=INFO
DRY_RUN=false
```

### CLI Interface
```bash
ai-code-review [OPTIONS] [PROJECT_ID] [MR_IID]

Options:
  --gitlab-url TEXT      GitLab instance URL (or use CI_SERVER_URL)
  --project-id TEXT      Project ID (or use CI_PROJECT_PATH)
  --mr-iid INTEGER       MR IID (or use CI_MERGE_REQUEST_IID)
  --provider TEXT        AI provider (ollama, gemini, openai, anthropic)
  --model TEXT           AI model to use (default: qwen2.5-coder:7b for ollama)
  --ollama-url TEXT      Ollama server URL (default: http://localhost:11434)
  --language-hint TEXT   Programming language hint
  --max-chars INTEGER    Maximum diff characters
  --max-files INTEGER    Maximum number of files
  --post                 Post review as MR note
  --with-summary         Include MR summary
  --enable-context       Enable project context injection
  --context-file PATH    Custom project context file path
  --context-url URL      External project context URL
  --auto-discovery       Auto-discover context files (README, CLAUDE.md, etc.)
  --timeout INTEGER      Operation timeout in seconds (default: 1800)
  --retry-count INTEGER  API retry attempts (default: 3)
  --dry-run              Dry run mode (no API calls)
  --config-file PATH     Configuration file path
  --log-level TEXT       Logging level
  --help                 Show help message

Exit Codes:
  0    Success - Review completed successfully
  1    General error (configuration, network, etc.)
  2    GitLab API error (authentication, permissions, etc.)
  3    AI provider error (API limits, model unavailable, etc.)
  4    Timeout error
  5    Empty MR (no changes to review)
```

### GitLab CI Usage
```bash
# Automatic mode (uses CI environment variables)
ai-code-review --post --with-summary --enable-context

# Manual mode (specify parameters)
ai-code-review --project-id "$CI_PROJECT_PATH" --mr-iid "$CI_MERGE_REQUEST_IID" --post
```

## 📈 Development Phases

### Phase 1: Local Development Foundation
- Project setup with modern Python tooling (uv, ruff, mypy, pytest)
- Basic GitLab integration with python-gitlab
- **Ollama integration with qwen2.5-coder:7b** (local development only)
- LangChain foundation with prompt templates and chains
- CLI interface with click
- Comprehensive testing framework with local LLM mocking

### Phase 2: LangChain Integration & Cloud Providers
- Complete LangChain implementation for all AI operations
- Gemini integration via langchain-google-genai (production/container default)
- Additional cloud providers (OpenAI, Anthropic) for production use
- Advanced configuration management with pydantic
- Improved error handling and logging with structlog

### Phase 3: Production Ready
- Container deployment with cloud providers only (Gemini default)
- CI/CD pipeline with cloud provider integration
- Documentation and deployment examples
- Performance monitoring and metrics

### Phase 4: Advanced Features
- Enhanced cloud provider support and load balancing
- Full customizable prompt template system
- Plugin system for custom reviewers
- Advanced project context integration (external APIs, documentation sites)
- Advanced LangChain features (memory, agents, tools)
- Performance optimizations for cloud deployments

## 🎯 Success Criteria

### Functionality
- ✅ Generate high-quality code reviews comparable to current tool
- ✅ Support all GitLab MR workflows
- ✅ Handle edge cases gracefully
- ✅ Provide clear, actionable feedback

### Quality
- ✅ 90%+ test coverage
- ✅ Zero mypy errors in strict mode
- ✅ All ruff checks pass
- ✅ Comprehensive documentation

### Performance
- ✅ <30s review generation for typical MRs
- ✅ Handle large MRs (100+ files) efficiently
- ✅ Minimal resource usage

### Maintainability
- ✅ Modular, extensible architecture
- ✅ Clear separation of concerns
- ✅ Easy to add new AI providers
- ✅ Comprehensive error handling