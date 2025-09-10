# Project Specifications: AI-Powered Code Review Tool

## 📑 Table of Contents

- [📋 Project Overview](#-project-overview)
  - [Core Functionality](#core-functionality)
  - [Usage Model](#usage-model)
  - [Technical Implementation](#technical-implementation)
- [🎯 Functional Requirements](#-functional-requirements)
  - [Core Features](#core-features-all-implemented-)
  - [FR-001: Multi-Platform Integration](#fr-001-multi-platform-integration-implemented)
  - [FR-002: AI Code Review](#fr-002-ai-code-review-implemented)
  - [FR-003: MR Summary Generation](#fr-003-mr-summary-generation-implemented)
  - [FR-004: Output Flexibility](#fr-004-output-flexibility-implemented)
  - [FR-005: Configuration Management](#fr-005-configuration-management-implemented)
  - [FR-006: Multi-Provider AI Support](#fr-006-multi-provider-ai-support-implemented)
  - [FR-007: Enterprise & Self-Hosted Support](#fr-007-enterprise--self-hosted-support-implemented)
  - [FR-008: Project Context Integration](#fr-008-project-context-integration-implemented)
  - [FR-009: Enhanced Review Integration](#fr-009-enhanced-review-integration-implemented)
  - [FR-010: Customizable Prompt Templates](#fr-010-customizable-prompt-templates-partially-implemented)
  - [FR-011: Content Processing](#fr-011-content-processing-implemented)
  - [FR-012: Error Handling & Resilience](#fr-012-error-handling--resilience-implemented)
  - [FR-013: Local Git Integration](#fr-013-local-git-integration-new-feature---implemented)
- [🔧 Non-Functional Requirements](#-non-functional-requirements)
  - [Performance](#performance)
  - [Reliability](#reliability)
  - [Security](#security)
  - [Maintainability](#maintainability)
  - [Usability](#usability)
- [🛠️ Technology Stack](#️-technology-stack)
  - [Core Technologies](#core-technologies)
  - [Development Tools](#development-tools)
  - [Dependencies](#dependencies)
  - [Development Infrastructure](#development-infrastructure)
  - [Container Specifications](#container-specifications)
- [🎯 AI Review Output Requirements](#-ai-review-output-requirements)
  - [Required Output Format](#required-output-format)
  - [Content Requirements](#content-requirements)
  - [Input Processing](#input-processing)
  - [Output Validation](#output-validation)
- [🏗️ Architecture Design](#️-architecture-design)
  - [Project Structure](#project-structure)
  - [Key Components](#key-components)
- [🧪 Testing Strategy](#-testing-strategy)
  - [Unit Tests](#unit-tests-90-coverage-target)
  - [Integration Tests](#integration-tests)
  - [Test Tools and Fixtures](#test-tools-and-fixtures)
- [🔧 Configuration Schema](#-configuration-schema)
  - [Environment Variables](#environment-variables)
  - [CLI Interface](#cli-interface)
  - [Platform CI Usage](#platform-ci-usage)
- [📈 Development Phases](#-development-phases)
- [🎯 Success Criteria](#-success-criteria)

---

## 📋 Project Overview

AI-powered Python CLI tool that provides automated code review assistance for
**GitLab Merge Requests**, **GitHub Pull Requests**, and **Local Git changes**. The tool analyzes diffs using AI models and generates
structured feedback to support human reviewers in identifying potential issues,
security vulnerabilities, and code quality improvements across three main workflows:

1. **Local Code Review**: Review uncommitted/unpushed changes in your local Git repository
2. **Remote Code Review**: Analyze existing MRs/PRs from the terminal with optional posting
3. **CI Integration**: Automated reviews in GitLab CI and GitHub Actions pipelines

### Core Functionality

**Code Analysis**: Analyzes code changes from multiple sources:
- Local Git repository changes (uncommitted/unpushed) using GitPython
- Remote MR diffs from GitLab API
- Remote PR diffs from GitHub API
Focuses on logic issues, security concerns, performance problems, and architectural
patterns with high-level feedback that complements static analysis tools.

**Context Integration**: Implemented feature to read project documentation (`.ai_review/project.md`)
to provide contextually relevant reviews that align with project-specific practices and conventions.

**Structured Output**: Generates markdown reviews with multiple formats:
- **Full Format**: Collapsible sections with MR summaries for remote/CI workflows
- **Local Format**: Terminal-friendly simplified markdown for local development
File-by-file analysis, actionable suggestions, and executive summaries
suitable for both technical and non-technical stakeholders across all workflows.

### Usage Model

The tool supports **three primary workflows**:

1. **Local Development**: Run directly from your Git repository to review uncommitted/unpushed changes before creating MRs/PRs
2. **Remote Analysis**: Analyze existing MRs/PRs from the terminal with optional posting to discussions
3. **CI/CD Integration**: Automated reviews in GitLab CI/GitHub Actions pipelines that fetch diffs and post reviews as **discussion threads** (GitLab) or **comments** (GitHub)

This provides immediate feedback to assist human reviewers without replacing the human review process.

### Technical Implementation

Built with Python 3.12+, LangChain for AI provider abstraction, GitPython for local Git operations, and modern
development tooling (uv, ruff, mypy). Supports three deployment modes:
- **Local Development**: Ollama + Local Git analysis (no external dependencies)
- **Remote Terminal**: Cloud providers for analyzing remote MRs/PRs
- **CI/CD Integration**: Containerized deployment with cloud AI providers (Gemini default, Anthropic alternative)
Full multi-platform support for GitLab, GitHub, and Local Git repositories.

## 🎯 Functional Requirements

### Core Features (All Implemented ✅)

### FR-001: Multi-Platform Integration (Implemented)

**GitLab Support:**

- ✅ Fetch MR diffs from GitLab API using project ID and MR IID
- ✅ Support both numeric project IDs and URL-encoded paths (e.g., `group/subgroup/project`)
- ✅ Handle authentication via GitLab Personal Access Token
- ✅ Support configurable GitLab instance URLs (including self-hosted)
- ✅ Post reviews as **discussion threads** with auto-resolution of previous AI threads
- ✅ SSL certificate support for internal GitLab instances

**GitHub Support:**

- ✅ Fetch PR diffs from GitHub API using owner/repo and PR number
- ✅ Handle authentication via GitHub Personal Access Token or GitHub Actions token
- ✅ Support configurable GitHub API URLs (GitHub.com and GitHub Enterprise)
- ✅ Post reviews as **PR comments**
- ✅ Full integration with GitHub Actions workflows

**Local Git Support:**

- ✅ Analyze uncommitted and unpushed changes directly from Git repository
- ✅ Compare against target branch (main, develop, custom) using merge-base
- ✅ GitPython integration for robust Git operations
- ✅ Terminal-friendly output format (simplified markdown without collapsible sections)
- ✅ Branch freshness validation with helpful warnings
- ✅ Support for detached HEAD states and complex Git scenarios

**Auto-Detection:**

- ✅ Automatic platform detection from CI/CD environment variables
- ✅ GitLab CI: Uses `CI_PROJECT_PATH`, `CI_MERGE_REQUEST_IID`, `CI_SERVER_URL`
- ✅ GitHub Actions: Uses `GITHUB_REPOSITORY`, `GITHUB_EVENT_PATH`, `GITHUB_API_URL`

### FR-002: AI Code Review (Implemented)

- ✅ Generate comprehensive code reviews using AI models
- ✅ Focus on high-level feedback: logic, correctness, security, performance, architecture
- ✅ Ignore trivial formatting/linting issues
- ✅ Provide actionable suggestions with code snippets
- ✅ Support multiple AI providers (Gemini production, Ollama local)
- ✅ Structured markdown output with collapsible sections

### FR-003: MR Summary Generation (Implemented)

- ✅ Generate unified reviews with executive summaries
- ✅ Business-friendly format for non-technical stakeholders
- ✅ Include headline, key changes, impact assessment, and risk level
- ✅ Single LLM invocation for efficiency (combined review + summary)

### FR-004: Output Flexibility (Implemented)

- ✅ Print reviews to stdout for CLI workflows
- ✅ Post reviews directly as MR notes in GitLab
- ✅ Unified review format (combines review and summary)
- ✅ Health check mode for connectivity testing

### FR-005: Configuration Management (Implemented)

- ✅ Environment variable configuration with validation
- ✅ Command-line argument overrides
- ✅ **YAML configuration file support**
- ✅ **Layered configuration priority system**
- ✅ Support for language hints and content limits
- ✅ Dry-run mode for testing without API calls

**Configuration File Features:**
- ✅ Auto-detection of `.ai_review/config.yml`
- ✅ Custom config file path via `--config-file` option
- ✅ Disable config file loading via `--no-config-file` flag
- ✅ Environment variables: `CONFIG_FILE`, `NO_CONFIG_FILE`
- ✅ Full YAML validation with comprehensive error messages
- ✅ **Priority Order**: CLI args > Env vars > Config file > Field defaults

**Performance Optimizations:**
- ✅ Lazy imports (`yaml`, `pathlib.Path`) - only loaded when needed
- ✅ Zero overhead when config files are disabled
- ✅ Efficient file existence checks before parsing
- ✅ Adaptive context windows and file filtering
- ✅ Comprehensive logging configuration

### Advanced Features

### FR-006: Multi-Provider AI Support (Implemented)

**Currently Implemented:**
- **Local Development**: Ollama with qwen2.5-coder:7b (local development only, cost-free)
- **Production Default**: Google Gemini (gemini-2.5-pro)
- **High-Quality Alternative**: Anthropic Claude (claude-sonnet-4-20250514)

**Planned (Not Implemented):**
- **OpenAI GPT Models**: Future consideration

**Provider Features:**
- ✅ Health check endpoints for all providers
- ✅ Provider-specific model defaults and validation
- ✅ Automatic API key validation and error handling
- ✅ Dry-run mode support across all providers
- ✅ Provider-specific timeout and retry handling

**Planned Future Support:**
- Provider load balancing and fallback mechanisms
- Extended model selection per provider
- Cost optimization with provider switching
- Additional local LLM providers beyond Ollama

**Architecture Features:**
- Extensible provider system via LangChain abstraction
- Provider-specific configuration and error handling
- Adaptive context windows based on diff size and provider capabilities

### FR-007: Enterprise & Self-Hosted Support (Implemented)

**SSL Certificate Support:**
- ✅ Custom SSL certificate support for internal GitLab instances
- ✅ SSL verification bypass for development environments
- ✅ Configurable SSL settings per GitLab instance

**Self-Hosted Platform Support:**
- ✅ GitLab self-hosted instances with custom URLs
- ✅ GitHub Enterprise support with custom API URLs
- ✅ Environment-specific configuration management

### FR-008: Project Context Integration (Implemented)

**Implemented:**
- **Standard Context File**: `.ai_review/project.md` - project info, stack, architecture, style guides
- **CI/CD Configuration**: Environment variable `ENABLE_PROJECT_CONTEXT=true/false` (default: true)
- **CLI Configuration**: `--project-context` / `--no-project-context` flags
- **Custom Path Mode**: Specify custom path within repo via `--context-file` or env var `PROJECT_CONTEXT_FILE`
- **Automatic Loading**: Context loaded automatically if file exists and feature enabled
- **Safe Error Handling**: Graceful fallback if file can't be read

**Future Implementation:**
- **Auto-discovery Mode**: Automatically find README.md, CLAUDE.md, .cursorrules, etc.
- **External URL Mode**: Fetch context from external URL (documentation sites)
- **Token Management**: Smart truncation when context + diff exceeds token limits

### FR-009: Enhanced Review Integration (Implemented)

**GitLab Discussion Threads:**
- ✅ Create reviews as **discussion threads** instead of simple comments
- ✅ Auto-resolution of previous AI-generated threads before posting new reviews
- ✅ Collapsible review content (collapses automatically after page refresh)
- ✅ Clean thread titles with review content as replies

**GitHub PR Comments:**
- ✅ Standard PR comment integration
- ✅ Rich markdown formatting support
- ✅ Integration with GitHub Actions permissions

**Review Format Management:**
- ✅ Configurable review formats (full vs compact)
- ✅ Optional MR Summary section (`include_mr_summary`)
- ✅ CLI flag support (`--no-mr-summary`)

### FR-010: Customizable Prompt Templates (Partially Implemented)

**Implemented Features:**
- ✅ Configurable review output formats (full vs compact)
- ✅ Optional MR Summary section (`include_mr_summary` configuration)
- ✅ Template constants for maintainable prompt management
- ✅ LangChain factory pattern for configuration integration

**Future Implementation:**
- Template override system via `.ai_review/templates/` directory
- Base template inheritance with custom extensions
- Advanced configurable review focus areas
- Project-specific guidelines integration

### FR-011: Content Processing (Implemented)

**Current Features:**
- ✅ Handle large diffs with intelligent truncation (adaptive context windows)
- ✅ File count and character limits (configurable via MAX_FILES/MAX_CHARS)
- ✅ Smart file filtering (exclude lockfiles, build artifacts, minified files)
- ✅ Adaptive context windows (16K standard, 24K for large diffs)
- ✅ Diff parsing and formatting for AI consumption

**Planned Enhancements:**
- Context-aware content prioritization based on project context

### FR-012: Error Handling & Resilience (Implemented)

**Current Features:**
- ✅ Custom exception hierarchy for different error types
- ✅ CI/CD specific error handling with appropriate exit codes (0-5)
- ✅ Provider availability checks (health-check functionality)
- ✅ Dry-run mode for testing without API calls
- ✅ HTTP timeout configuration for API calls
- ✅ Structured logging for troubleshooting
- ✅ SSL certificate validation and error handling
- ✅ GitPython error handling for local Git operations

**Planned Enhancements:**
- API failure retry logic with backoff strategies
- Graceful degradation on partial failures
- Advanced rate limit handling
- Network resilience improvements

### FR-013: Local Git Integration (New Feature - Implemented)

**Core Functionality:**
- ✅ **Local Change Analysis**: Review uncommitted and unpushed changes in current Git repository
- ✅ **Smart Merge Base**: Calculate diff against target branch using Git merge-base algorithm
- ✅ **Branch Comparison**: Support for custom target branches (main, develop, etc.)
- ✅ **GitPython Integration**: Robust Git operations without external git binary dependency in tests
- ✅ **Terminal-Optimized Output**: Simplified markdown format without collapsible sections

**Advanced Features:**
- ✅ **Branch Freshness Check**: Warn users when local target branch is behind remote origin
- ✅ **Detached HEAD Support**: Handle complex Git states gracefully
- ✅ **File Filtering**: Apply same exclusion patterns as remote reviews
- ✅ **Commit History**: Include local commit information in analysis context
- ✅ **Project URL Generation**: File-based URLs for local repository context

**CLI Integration:**
- ✅ `--local` flag to enable local Git analysis mode
- ✅ `--target-branch` option to specify comparison branch (defaults to main)
- ✅ `--output-file` support for saving local reviews to files

**Use Cases:**
- Pre-commit code quality checks
- Feature branch review before creating MR/PR
- Local development workflow integration
- Offline code analysis without platform APIs

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

**Core Runtime Dependencies:**
- **CLI Framework**: `click` (modern CLI interface with better UX)
- **HTTP Clients**: `aiohttp` + `httpx` (async HTTP for better performance)
- **Platform APIs**: `python-gitlab` (GitLab integration), `PyGithub` (GitHub integration)
- **Git Operations**: `GitPython` (local Git repository analysis)
- **LLM Framework**: `langchain` + `langchain-community` (prompt management, LLM abstraction)

**AI Providers (Implemented):**
- **Local Development**: `ollama` + `langchain-ollama` (cost-free local LLM)
- **Production**: `langchain-google-genai` (Gemini integration)
- **High-Quality Alternative**: `langchain-anthropic` (Claude integration)

**Configuration & Validation:**
- **Settings Management**: `pydantic` v2+ + `pydantic-settings` (validation and settings)
- **Logging**: `structlog` (structured logging)

**Development Dependencies:**
- **Code Quality**: `ruff` (linting/formatting), `mypy` (type checking)
- **Testing**: `pytest` + `pytest-asyncio` + `pytest-mock` + `pytest-cov`
- **Security**: `bandit` (security linting)
- **Git Hooks**: `pre-commit` (automated code quality checks)

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

## 🎯 AI Review Output Requirements

The AI system must generate structured code reviews that serve both technical and business audiences. The output should follow a unified format that combines executive summary with detailed technical analysis.

### Required Output Format

The AI must generate reviews following one of two configurable structures:

#### Full Format (Default, `include_mr_summary=true`)

```markdown
## AI Code Review

### 📋 MR Summary
[Single sentence describing the main change]

- **Key Changes:** [List 2-3 most important changes]
- **Impact:** [Describe affected modules/functionality]
- **Risk Level:** [Low/Medium/High] - [Brief reason]

### Detailed Code Review
[Technical analysis focusing on logic, security, performance, architecture]

#### 📂 File Reviews
[Only include if specific file feedback exists]

<details>
<summary><strong>📄 `filename`</strong> - Brief issue summary</summary>

- **[Review]** Actionable review with reasoning
- **[Question]** Clarifying questions (if needed)
- **[Suggestion]** Improvement suggestions (if needed)

</details>

### ✅ Summary
- **Overall Assessment:** [Quality rating + key recommendations]
- **Priority Issues:** [Most critical items]
- **Minor Suggestions:** [Optional improvements]
```

#### Compact Format (`include_mr_summary=false`, `--no-mr-summary`)

```markdown
## AI Code Review

### Detailed Code Review
[Technical analysis focusing on logic, security, performance, architecture]

#### 📂 File Reviews
[Only include if specific file feedback exists]

<details>
<summary><strong>📄 `filename`</strong> - Brief issue summary</summary>

- **[Review]** Actionable review with reasoning
- **[Question]** Clarifying questions (if needed)
- **[Suggestion]** Improvement suggestions (if needed)

</details>

### ✅ Summary
- **Overall Assessment:** [Quality rating + key recommendations]
- **Priority Issues:** [Most critical items]
- **Minor Suggestions:** [Optional improvements]
```

#### Local Format (`--local` workflow)

```markdown
## AI Code Review

### Code Analysis
[Technical analysis focusing on logic, security, performance, architecture]

**Files Changed:** file1.py, file2.js, file3.md

#### 📄 file1.py
- **[Review]** Actionable review with reasoning
- **[Suggestion]** Improvement suggestions

#### 📄 file2.js
- **[Review]** Actionable review with reasoning

### ✅ Summary
- **Overall Assessment:** [Quality rating + key recommendations]
- **Priority Issues:** [Most critical items]
- **Minor Suggestions:** [Optional improvements]
```

### Content Requirements

#### Technical Analysis Focus Areas

The AI must analyze and comment on:

1. **Logic & Correctness**: Algorithm correctness, edge case handling, potential bugs
2. **Security**: Vulnerability identification, authentication/authorization issues, data validation
3. **Performance**: Efficiency concerns, scalability implications, resource usage
4. **Architecture**: Design patterns, code organization, maintainability
5. **Best Practices**: Language-specific conventions, error handling, testing considerations

#### Quality Standards

- **Actionable Feedback**: Every suggestion must include specific reasoning and recommended solution
- **High-Level Focus**: Ignore trivial formatting issues that linters catch automatically
- **Contextual Relevance**: Analysis should consider the programming language and project context when available
- **Professional Tone**: Collaborative and constructive feedback suitable for team environments

### Input Processing

The AI system receives:

- **Diff Content**: Git diff showing code changes
- **Language Hint** (optional): Primary programming language for context
- **Project Context** (optional): Project-specific information, standards, architecture details

### Output Validation

Generated reviews must:

- Start with exactly "## AI Code Review"
- Follow the specified section structure without deviation
- Provide concise, focused analysis within reasonable length limits
- Include specific code examples when making suggestions
- Balance technical depth with accessibility for different stakeholders

## 🏗️ Architecture Design

### Project Structure

```
ai-code-review/
├── src/ai_code_review/
│   ├── __init__.py
│   ├── cli.py                        # CLI entry point with 3 workflow support
│   ├── models/                       # Pydantic models
│   │   ├── __init__.py
│   │   ├── config.py                 # Configuration models with platform auto-detection
│   │   ├── platform.py               # Platform-agnostic data models (GitLab + GitHub + Local)
│   │   └── review.py                 # Review data models
│   ├── core/                         # Core business logic
│   │   ├── __init__.py
│   │   ├── base_platform_client.py   # Abstract platform client interface
│   │   ├── gitlab_client.py          # GitLab API client with SSL support
│   │   ├── github_client.py          # GitHub API client
│   │   ├── local_git_client.py       # Local Git operations with GitPython
│   │   └── review_engine.py          # Multi-platform review orchestration
│   ├── providers/                    # AI provider implementations via LangChain
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract base provider using LangChain
│   │   ├── ollama.py                 # Ollama local LLM implementation
│   │   ├── gemini.py                 # Gemini implementation via langchain-google-genai
│   │   └── anthropic.py              # Anthropic Claude implementation
│   └── utils/                        # Utility functions
│       ├── __init__.py
│       ├── prompts.py                # LangChain prompt templates with multi-format support
│       ├── exceptions.py             # Custom exceptions
│       ├── platform_exceptions.py   # Platform-specific exceptions
│       └── ssl_utils.py              # SSL certificate utilities
├── tests/
│   ├── conftest.py                   # Shared test utilities and GitPython mocking
│   ├── unit/                         # Comprehensive unit tests (89% coverage)
│   ├── integration/                  # End-to-end workflow tests
│   └── fixtures/                     # Test data and mock responses
├── docs/                             # Comprehensive documentation
│   ├── user-guide.md                 # 3 use cases guide
│   ├── developer-guide.md            # Architecture and development guide
│   └── developer-guide-footer.md     # Shared documentation components
├── .ai_review/                       # Project context for AI reviews
├── pyproject.toml
├── uv.lock
└── README.md
```

### Key Components

#### Configuration Management

- Pydantic models for type-safe configuration
- Environment variable loading with validation
- CLI argument parsing and merging
- Support for config files (TOML/YAML)

#### Platform Integration

**GitLab Integration:**
- Async HTTP client for GitLab API
- Robust error handling and retry logic
- Support for multiple GitLab instances
- SSL certificate support for internal instances
- Discussion thread management

**GitHub Integration:**
- GitHub API client with Enterprise support
- Pull Request diff analysis
- Comment posting and management
- GitHub Actions integration

**Local Git Integration:**
- GitPython for repository operations
- Smart merge-base calculations
- Branch freshness validation
- Detached HEAD state handling

#### AI Provider Abstraction via LangChain

- LangChain-based unified interface for all AI providers
- Consistent prompt management using LangChain templates
- Provider-specific configuration through LangChain integrations
- Easy addition of new providers through LangChain ecosystem
- Built-in retry logic and error handling from LangChain

#### Review Engine (Implemented)

- **Core Functionality**: Orchestrates unified review and summary generation using LangChain chains
- **Prompt Management**: LangChain prompt templates with structured output requirements
- **Provider Integration**: Unified interface to Ollama and Gemini providers
- **Content Processing**: Adaptive context windows and intelligent diff truncation
- **File Filtering**: Smart exclusion of build artifacts, lockfiles, and generated content
- **Output Generation**: Structured markdown reviews with collapsible sections

#### Project Context Handler (Implemented)

**Current Implementation:**
- ✅ Standard context file support (`.ai_review/project.md`)
- ✅ Context size management and intelligent truncation
- ✅ Safe file loading with graceful fallback
- ✅ CLI control (`--project-context`/`--no-project-context`)
- ✅ Environment variable control (`ENABLE_PROJECT_CONTEXT`)

**Future Implementation:**
- Auto-discovery of standard files (README.md, CLAUDE.md, .cursorrules)
- External URL context fetching with caching
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
- **Multi-Platform API Integration:**
  - GitLab API integration (Merge Requests, discussion threads)
  - GitHub API integration (Pull Requests, comments)
  - Local Git integration (GitPython, uncommitted/unpushed changes)
- **AI Provider Integration:**
  - Ollama local LLM integration (local development only)
  - Google Gemini cloud provider integration
  - Anthropic Claude cloud provider integration
- **CI/CD Platform Testing:**
  - GitLab CI/CD with automatic platform detection
  - GitHub Actions with automatic platform detection
- **Local Development Testing:**
  - Git repository state testing
  - Branch comparison and merge-base validation
  - Terminal output format verification
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
# Platform Access Tokens (choose based on workflow)
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx  # For GitLab platform (not needed for --local)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx   # For GitHub platform (not needed for --local)

# Platform Configuration
PLATFORM_PROVIDER=gitlab                # gitlab, github, or local (auto-detected in CI/CD)
GITLAB_URL=https://gitlab.com           # GitLab instance URL (supports self-hosted)
GITHUB_URL=https://api.github.com       # GitHub API URL (supports Enterprise)

# Local Git Configuration (for --local workflow)
# No tokens required for local analysis - uses GitPython directly

# Core AI Configuration
AI_PROVIDER=gemini                      # gemini, anthropic, ollama (openai: configured but not implemented)
AI_MODEL=gemini-2.5-pro                 # AI model name for selected provider
AI_API_KEY=your_gemini_api_key_here     # Required for cloud providers (not needed for ollama)

# AI Model Parameters (defaults optimized for code review)
TEMPERATURE=0.1                         # 0.0-2.0, lower = more deterministic
MAX_TOKENS=8000                         # Maximum response tokens
HTTP_TIMEOUT=5.0                        # HTTP timeout in seconds

# Ollama Configuration (for local development)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama server URL

# Processing Limits
MAX_CHARS=100000                        # Max characters from diff
MAX_FILES=100                           # Max files to process

# Review Format Configuration
INCLUDE_MR_SUMMARY=true                 # Include MR Summary section (set to false for compact format)

# GitLab CI/CD Variables (automatically set in CI/CD environment)
CI_PROJECT_PATH=                        # Project path (group/project)
CI_MERGE_REQUEST_IID=                   # MR IID number
CI_SERVER_URL=                          # GitLab instance URL

# GitHub Actions Variables (automatically set in GitHub Actions environment)
GITHUB_REPOSITORY=                      # Repository (owner/repo)
GITHUB_EVENT_PATH=                      # Path to GitHub event JSON
GITHUB_API_URL=                         # GitHub API URL

# Optional Features
LANGUAGE_HINT=python                    # Programming language hint
DRY_RUN=false                           # Enable dry-run mode (no API calls)
BIG_DIFFS=false                         # Force large context (24K) - auto-activated for diffs >60K chars
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Configuration File Options
NO_CONFIG_FILE=false                    # Skip loading config file (auto-detected or custom)
CONFIG_FILE=                            # Custom config file path (default: auto-detect .ai_review/config.yml)

# File Filtering (comma-separated glob patterns)
EXCLUDE_PATTERNS=*.lock,*.min.js,node_modules/**,dist/**,build/**
```

**Configuration Notes:**
- URLs are validated for proper format
- AI model names are validated for basic format requirements
- Log levels are validated against standard Python logging levels
- `EXCLUDE_PATTERNS` can be set to empty string to disable all filtering
- `BIG_DIFFS` is auto-activated for diffs >60K characters for optimal performance

**Configuration File Features:**
- **Auto-detection**: `.ai_review/config.yml` loaded automatically if it exists
- **Priority order**: CLI args > Environment variables > Config file > Field defaults
- **YAML format**: Supports all environment variables in YAML key: value format
- **Custom paths**: Use `CONFIG_FILE` env var or `--config-file` CLI option
- **Disable loading**: Use `NO_CONFIG_FILE=true` or `--no-config-file` flag
- **Performance**: Uses lazy imports, zero overhead when disabled
- **Validation**: Full YAML syntax validation with descriptive error messages
- **Local mode** requires Git repository and optional Git binary (GitPython handles most operations)
- Platform tokens not required for `--local` workflow

### CLI Interface

```bash
# Multi-workflow support
ai-code-review [OPTIONS] [PROJECT_ID] [MR_IID]  # Remote workflow
ai-code-review --local [OPTIONS]                # Local workflow

Core Options:
  --local                     Enable local Git review mode (analyze uncommitted/unpushed changes)
  --target-branch TEXT        Target branch for local comparison (default: main)

Platform Options:
  --gitlab-url TEXT           GitLab instance URL (or use CI_SERVER_URL)
  --github-url TEXT           GitHub API URL (or use GITHUB_API_URL)
  --project-id TEXT           Project ID (or use CI_PROJECT_PATH)
  --mr-iid INTEGER            MR IID (or use CI_MERGE_REQUEST_IID)
  --owner TEXT                GitHub repository owner
  --repo TEXT                 GitHub repository name
  --pr-number INTEGER         GitHub PR number

AI Provider Options:
  --provider [ollama|gemini|anthropic]  AI provider to use (gemini default)
  --model TEXT                AI model name (provider-specific defaults)
  --ollama-url TEXT           Ollama server URL (http://localhost:11434 default)
  --temperature FLOAT         AI temperature 0.0-2.0 (0.1 default)
  --max-tokens INTEGER        Maximum AI response tokens (8000 default)

Processing Options:
  --language-hint TEXT        Programming language hint
  --max-chars INTEGER         Maximum diff characters to process (100000 default)
  --max-files INTEGER         Maximum number of files to process (100 default)
  --exclude-files TEXT        Additional file patterns to exclude (can be repeated)
  --no-file-filtering         Disable all file filtering (include lockfiles, etc.)

Output Options:
  --post                      Post review as platform comment/discussion
  --output-file PATH          Save review to file (supports local workflow)
  --no-mr-summary             Disable MR summary section (compact format)

Configuration File Options:
  --config-file PATH          Custom config file path (default: auto-detect .ai_review/config.yml)
  --no-config-file            Skip loading config file (auto-detected or specified)

Development Options:
  --dry-run                   Dry run mode (no API calls, for testing)
  --big-diffs                 Force large context window (24K tokens)
  --log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]  Logging level
  --health-check              Check AI provider connectivity and exit
  --help                      Show help message

Exit Codes:
  0    Success - Review completed successfully
  1    General error (configuration, network, etc.)
  2    Platform API error (authentication, permissions, etc.)
  3    AI provider error (API limits, model unavailable, etc.)
  4    Timeout error
  5    Empty changes (no changes to review)
```

**CLI Usage Examples:**

```bash
# LOCAL WORKFLOW - Review uncommitted/unpushed changes
ai-code-review --local                                    # Compare against main branch
ai-code-review --local --target-branch develop           # Compare against develop
ai-code-review --local --provider ollama                 # Use Ollama for local analysis
ai-code-review --local --output-file review.md           # Save local review to file

# REMOTE WORKFLOW - Analyze existing MRs/PRs
AI_API_KEY=your_key ai-code-review group/project 123     # GitLab MR analysis
AI_API_KEY=your_key ai-code-review --owner user --repo project --pr-number 456  # GitHub PR
ai-code-review group/project 123 --provider ollama       # Local Ollama for remote MR

# CI/CD WORKFLOW - Automated reviews
ai-code-review --post                                     # Auto-detect from CI environment
AI_API_KEY=your_key ai-code-review --post                # Post review to MR/PR

# ADVANCED OPTIONS
ai-code-review --local --big-diffs --exclude-files "*.lock"        # Large local changes
AI_API_KEY=your_key ai-code-review group/project 123 --no-mr-summary  # Compact format
ai-code-review --health-check --provider gemini                    # Provider connectivity
```

### Platform CI Usage

**GitLab CI:**
```bash
# Automatic mode (uses CI environment variables)
ai-code-review --post

# Manual mode (specify parameters explicitly)
ai-code-review --project-id "$CI_PROJECT_PATH" --mr-iid "$CI_MERGE_REQUEST_IID" --post

# With health check for reliability
ai-code-review --health-check && ai-code-review --post
```

**GitHub Actions:**
```bash
# Automatic mode (uses GitHub environment variables)
ai-code-review --post

# Manual mode with explicit parameters
ai-code-review --owner "$GITHUB_REPOSITORY_OWNER" --repo "$GITHUB_REPOSITORY_NAME" --pr-number "$PR_NUMBER" --post
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
- ✅ Support all GitHub PR workflows
- ✅ Support local Git review workflows
- ✅ Handle edge cases gracefully across all 3 platforms
- ✅ Provide clear, actionable feedback in appropriate formats

### Quality

- ✅ 90%+ test coverage
- ✅ Zero mypy errors in strict mode
- ✅ All ruff checks pass
- ✅ Comprehensive documentation

### Performance Goals

- ✅ <30s review generation for typical MRs/PRs
- ✅ <5s local review generation for typical changes
- ✅ Handle large MRs (100+ files) efficiently across all platforms
- ✅ Minimal resource usage with smart context management

### Maintainability Goals

- ✅ Modular, extensible architecture with platform abstraction
- ✅ Clear separation of concerns across 3 workflow types
- ✅ Easy to add new AI providers via LangChain
- ✅ Easy to add new platforms via PlatformClientInterface
- ✅ Comprehensive error handling and CI compatibility
- ✅ 89% test coverage with robust GitPython mocking strategy
