# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Setup

```bash
# Install dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Setup environment (REQUIRED)
cp env.example .env
# Edit .env and set GITLAB_TOKEN and AI_API_KEY
```

### Code Quality & Testing

```bash
# Complete quality check pipeline
uv run pre-commit run --all-files

# Individual checks
uv run ruff check . --fix        # Auto-fix linting issues
uv run ruff format .             # Format code
uv run mypy src/                 # Type checking (strict mode)

# Testing
uv run pytest                    # Run all tests
uv run pytest --cov=src --cov-report=html    # With coverage report
uv run pytest tests/unit/test_cli.py -v      # Single test file with verbose
```

### Application Usage

```bash
# Health check (verify AI provider connectivity)
ai-code-review --health-check

# Local development with Ollama (no API key needed)
ai-code-review group/project 123 --provider ollama --dry-run

# Production with Gemini (requires API key)
AI_API_KEY=your_key ai-code-review group/project 123 --dry-run

# Post review to GitLab MR
ai-code-review group/project 123 --post
```

## High-Level Architecture

### System Overview

This is an **AI-powered CLI tool** that generates automated code reviews for GitLab Merge Requests. It's designed as a **CI/CD-ready application** with both local development support and production cloud deployment capabilities.

### Core Design Principles

#### Dual AI Strategy

- **Local Development**: Ollama with `qwen2.5-coder:7b` (cost-free, no API keys required)
- **Production/CI**: Google Gemini `gemini-2.5-pro` (default cloud provider)
- **Extensible**: LangChain abstraction allows easy addition of other providers (OpenAI, Anthropic)

#### Adaptive Context Management

- **Smart Sizing**: 16K context for standard MRs (≤60K chars), auto-expands to 24K for large MRs
- **File Filtering**: Automatically excludes lockfiles, build artifacts, minified files to reduce noise
- **No Truncation**: Intelligent filtering replaces traditional diff truncation

#### Unified Review Generation

- **Single LLM Call**: Combines detailed review + executive summary in one efficient request
- **Structured Output**: Enforces strict markdown format with collapsible sections
- **Business + Technical**: Serves both developer and stakeholder audiences

### Architecture Flow

```
CLI Input → Config Validation → GitLab Client → Review Engine → AI Provider → Structured Output
    ↓            ↓                    ↓               ↓             ↓              ↓
Arguments    Environment       MR Data Fetch    Context Prep   LangChain     Markdown +
+ Env Vars   + Validation      + Diff Parse     + Filtering    Invocation    GitLab Post
```

### Key Components

**Configuration System (`models/config.py`)**:
- **Pydantic-based**: Type-safe configuration with automatic validation
- **Priority Order**: CLI args → Environment vars → CI/CD vars → Defaults
- **Smart Validation**: Provider-model compatibility, token format validation, helpful error messages
- **Cloud Provider Detection**: Automatic API key requirement validation

**Review Engine (`core/review_engine.py`)**:
- **Orchestrator**: Coordinates GitLab API + AI provider interactions
- **Context Builder**: Formats diffs, adds commit history, applies file filtering
- **Adaptive Processing**: Dynamic context window sizing based on diff size
- **Error Recovery**: Comprehensive error handling with specific exit codes (0-5)

**AI Provider Abstraction (`providers/`)**:
- **LangChain Foundation**: Unified interface across Ollama, Gemini, future providers
- **Provider-Specific Logic**: Ollama health checks, Gemini API handling, model validation
- **Adaptive Context**: Each provider reports optimal context window sizes
- **Async Operations**: Non-blocking AI API calls with proper timeout handling

**GitLab Integration (`core/gitlab_client.py`)**:
- **Multi-Instance Support**: Works with GitLab.com and self-hosted instances
- **CI/CD Optimized**: Automatic detection of GitLab CI environment variables
- **Project ID Flexibility**: Handles both numeric IDs and path-based IDs (`group/project`)
- **MR Operations**: Fetch diffs, metadata, commit history, post review comments

**Prompt Management (`utils/prompts.py`)**:
- **Structured Templates**: LangChain prompt templates with strict output format enforcement
- **Context Injection**: Dynamic inclusion of project context, language hints, library docs
- **Format Validation**: Ensures AI follows exact markdown structure requirements
- **Chain Architecture**: Input transformation → Prompt → LLM → Parser pipeline

### Configuration Architecture

**Environment Priority System:**
1. **CLI Arguments** (highest): `--provider gemini --model gemini-2.5-pro`
2. **Environment Variables**: `AI_PROVIDER=gemini AI_MODEL=gemini-2.5-pro`
3. **CI/CD Variables**: `CI_PROJECT_PATH`, `CI_MERGE_REQUEST_IID` (auto-detected)
4. **Defaults** (lowest): Gemini production, Ollama local development

**Provider Configuration Patterns:**

```bash
# Local Development (no API keys)
AI_PROVIDER=ollama
AI_MODEL=qwen2.5-coder:7b
OLLAMA_BASE_URL=http://localhost:11434

# Production (API key required)
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-pro
AI_API_KEY=your_gemini_api_key_here
```

### Error Handling Strategy

**Exit Code System:**
- `0`: Success
- `1`: General configuration/network errors
- `2`: GitLab API errors (auth, permissions)
- `3`: AI provider errors (API limits, model unavailable)
- `4`: Timeout errors
- `5`: Empty MR (no changes to review)

**Failure Modes:**
- **AI Provider Unavailable**: Health check fails, suggests configuration fixes
- **Invalid Configuration**: Detailed validation errors with actionable guidance
- **Network Issues**: Timeout handling with configurable limits
- **CI/CD Integration**: Graceful failure without blocking pipelines (`allow_failure: true`)

### Development Patterns

**Testing Strategy:**
- **Unit Tests**: Mock all external dependencies (GitLab API, AI APIs)
- **Integration Tests**: Real Ollama testing locally, cloud provider testing in CI
- **Dry-Run Mode**: Full pipeline testing without API costs
- **Health Checks**: Connectivity verification before processing

**Code Organization:**
- **models/**: Pydantic models for configuration, GitLab data, review structures
- **core/**: Business logic (GitLab client, review engine)
- **providers/**: AI provider implementations with LangChain integration
- **utils/**: Shared utilities (prompts, exceptions, logging)

**Development Workflow:**
- **Pre-commit Hooks**: Automatic code quality checks on commit
- **Type Safety**: Strict mypy configuration with full annotation coverage
- **Modern Tooling**: uv for package management, ruff for linting/formatting
- **Structured Logging**: contextual logging for debugging and monitoring
