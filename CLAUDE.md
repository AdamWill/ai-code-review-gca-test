# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Setup

```bash
# Install dependencies (includes GitPython for local Git support)
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Setup environment (choose based on workflow)
cp env.example .env
# Or use YAML configuration for team consistency (v1.7.0+)
mkdir -p .ai_review && cp .ai_review/config.yml.example .ai_review/config.yml
# Edit .env/.ai_review/config.yml and set tokens based on your use case:
# - GITLAB_TOKEN: For GitLab MRs (not needed for --local)
# - GITHUB_TOKEN: For GitHub PRs (not needed for --local)
# - AI_API_KEY: For cloud providers (not needed for --provider ollama)
# - LOCAL workflow: Only needs Git repository (no tokens required)
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
uv run pytest --cov=src --cov-report=html    # With coverage report (75% required)
uv run pytest tests/unit/test_cli.py -v      # Single test file with verbose
uv run pytest --cov=src --cov-fail-under=75  # Enforce coverage threshold
```

### Application Usage

```bash
# Health check (verify AI provider connectivity)
ai-code-review --health-check

# LOCAL WORKFLOW - Review uncommitted/unpushed changes
ai-code-review --local                                   # Compare against main
ai-code-review --local --target-branch develop           # Compare against develop
ai-code-review --local --provider ollama --output-file review.md

# REMOTE WORKFLOW - Analyze existing MRs/PRs
ai-code-review group/project 123 --provider ollama --dry-run           # GitLab MR
ai-code-review --owner user --repo project --pr-number 456 --dry-run   # GitHub PR

# CI/CD WORKFLOW - Automated reviews (auto-detects platform)
ai-code-review --post                                    # GitLab or GitHub CI
AI_API_KEY=your_key ai-code-review --post                # With cloud provider

# FORMAT OPTIONS
ai-code-review group/project 123 --no-mr-summary         # Compact format
ai-code-review --local --provider gemini                 # Local with cloud AI

# Context Generation (separate tool for creating project context)
ai-generate-context                                    # Generate .ai_review/context.md
ai-generate-context --output custom-context.md         # Custom output file
ai-generate-context --provider ollama                  # Use local AI for generation

# Context7 Integration (enhanced library documentation)
# Set CONTEXT7_API_KEY environment variable to enable
ai-generate-context --enable-context7                  # Include Context7 docs
ai-code-review --local --provider gemini               # Reviews automatically use Context7 if enabled
```

## High-Level Architecture

### System Overview

This is an **AI-powered CLI tool** that generates automated code reviews for **GitLab Merge Requests**, **GitHub Pull Requests**, and **Local Git changes**. It includes a companion **AI context generator** for intelligent project documentation. The system supports **three primary workflows**:

1. **Local Code Review**: Analyze uncommitted/unpushed changes in your Git repository (`--local`)
2. **Remote Code Review**: Analyze existing MRs/PRs from terminal with optional posting
3. **CI/CD Integration**: Automated reviews in GitLab CI/GitHub Actions pipelines

The tool provides both **local development support** (Ollama, no API keys) and **production cloud deployment** capabilities (Gemini, Anthropic).

### Core Design Principles

#### Multi-Modal AI Strategy

- **Local Development**: Ollama with `qwen2.5-coder:7b` (cost-free, no API keys required)
- **Production/CI**: Google Gemini `gemini-2.5-pro` (default cloud provider)
- **High-Quality Alternative**: Anthropic Claude `claude-sonnet-4-20250514`
- **Extensible**: LangChain abstraction supports multiple providers

#### Adaptive Context Management

- **Smart Sizing**: 16K context for standard MRs (≤60K chars), auto-expands to 24K for large MRs
- **File Filtering**: Automatically excludes lockfiles, build artifacts, minified files to reduce noise
- **No Truncation**: Intelligent filtering replaces traditional diff truncation

#### Unified Review Generation

- **Single LLM Call**: Combines detailed review + executive summary in one efficient request
- **Multi-Format Output**:
  - **Full**: Collapsible sections with MR summaries (remote/CI workflows)
  - **Compact**: Same as Full but without MR summary (`--no-mr-summary`)
  - **Local**: Terminal-friendly simplified markdown (`--local` workflow)
- **Business + Technical**: Serves both developer and stakeholder audiences

### Architecture Flow

```
                                  ┌─ GitLab Client ─┐
                                  │                 │
CLI Input → Config Validation → Platform Factory → │ Review Engine │ → AI Provider → Structured Output
    ↓            ↓                  │                 │      ↓             ↓              ↓
Arguments    Environment         ├─ GitHub Client ─┤  Context Prep   LangChain     Format-Specific
+ Env Vars   + Auto-Detection    │                 │  + Filtering    Invocation    Markdown Output
                                  └─ Local Git ─────┘      ↓             ↓              ↓
                                                      File Analysis   Provider      Terminal/File/Post
                                                      + Diff Parse    Selection     Based on Workflow
```

**Platform Selection Logic:**
- **`--local`** → LocalGitClient (GitPython)
- **CI Environment** → Auto-detect GitLab/GitHub from env vars
- **Explicit args** → GitLab/GitHub client with provided credentials

### Key Components

**Configuration System (`models/config.py`)**:
- **Pydantic-based**: Type-safe configuration with automatic validation
- **Priority Order**: CLI args → Environment vars → CI/CD vars → Defaults
- **Smart Validation**: Provider-model compatibility, token format validation, helpful error messages
- **Cloud Provider Detection**: Automatic API key requirement validation

**Review Engine (`core/review_engine.py`)**:
- **Multi-Platform Orchestrator**: Coordinates GitLab/GitHub/Local Git + AI provider interactions
- **Factory Pattern**: Creates appropriate platform client based on configuration/CLI args
- **Context Builder**: Formats diffs, adds commit history, applies file filtering across all platforms
- **Format Selection**: Chooses output format (Full/Compact/Local) based on workflow
- **Adaptive Processing**: Dynamic context window sizing based on diff size
- **Error Recovery**: Comprehensive error handling with specific exit codes (0-5)

**AI Provider Abstraction (`providers/`)**:
- **LangChain Foundation**: Unified interface across Ollama, Gemini, future providers
- **Provider-Specific Logic**: Ollama health checks, Gemini API handling, model validation
- **Adaptive Context**: Each provider reports optimal context window sizes
- **Async Operations**: Non-blocking AI API calls with proper timeout handling

**Platform Integration (`core/` clients)**:

**GitLab Client (`core/gitlab_client.py`)**:
- **Multi-Instance Support**: Works with GitLab.com and self-hosted instances
- **CI/CD Optimized**: Automatic detection of GitLab CI environment variables
- **Project ID Flexibility**: Handles both numeric IDs and path-based IDs (`group/project`)
- **SSL Certificate Support**: Custom certificates for internal GitLab instances
- **Discussion Threads**: Posts reviews as collapsible discussion threads

**GitHub Client (`core/github_client.py`)**:
- **GitHub.com + Enterprise**: Full API support for both hosting types
- **Actions Integration**: Automatic detection of GitHub Actions environment
- **Repository Flexibility**: Handles owner/repo format for PR identification
- **PR Comments**: Posts reviews as standard PR comments

**Local Git Client (`core/local_git_client.py`)**:
- **GitPython Integration**: Direct Git repository analysis without external APIs
- **Smart Merge Base**: Calculates diffs against target branch using Git algorithms
- **Branch Validation**: Warns when local target branch is behind remote origin
- **Terminal Format**: Generates simplified markdown optimized for terminal viewing

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
# Local Git Reviews (no tokens needed, works offline)
AI_PROVIDER=ollama
AI_MODEL=qwen2.5-coder:7b
OLLAMA_BASE_URL=http://localhost:11434
# Usage: ai-code-review --local

# Remote Reviews with Local AI (GitLab/GitHub tokens needed)
AI_PROVIDER=ollama
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
# Usage: ai-code-review group/project 123

# Production CI/CD (API key required)
AI_PROVIDER=gemini
AI_MODEL=gemini-2.5-pro
AI_API_KEY=your_gemini_api_key_here
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx  # Or GITHUB_TOKEN for GitHub
# Usage: ai-code-review --post (in CI)

# Enhanced Context with Context7 (optional)
AI_PROVIDER=gemini
AI_API_KEY=your_gemini_api_key_here
CONTEXT7_API_KEY=ctx7_xxxxxxxxxxxxxxxxxxxx
# Usage: ai-generate-context --enable-context7
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
- **Unit Tests**: Mock all external dependencies (GitLab/GitHub APIs, AI APIs, GitPython in CI)
- **Integration Tests**: Real Ollama testing locally, cloud provider testing in CI, local Git testing
- **CI Compatibility**: GitPython mocking strategy for tests in environments without git binary
- **Dry-Run Mode**: Full pipeline testing without API costs across all 3 workflows
- **Health Checks**: Connectivity verification before processing for all providers

**Code Organization:**
- **models/**: Pydantic models for configuration, platform-agnostic data structures, review models
  - `config.py`: Multi-platform configuration with auto-detection
  - `platform.py`: Unified data models (PullRequestData, PlatformClientInterface)
  - `review.py`: Review and summary structures
- **core/**: Multi-platform business logic
  - `review_engine.py`: Orchestrates all 3 workflows with factory pattern
  - `gitlab_client.py`: GitLab API integration with SSL support
  - `github_client.py`: GitHub API integration
  - `local_git_client.py`: Local Git operations with GitPython
  - `base_platform_client.py`: Abstract interface for platform clients
- **providers/**: AI provider implementations with LangChain integration
  - `ollama.py`, `gemini.py`, `anthropic.py`: Provider-specific implementations
- **utils/**: Shared utilities
  - `prompts.py`: Multi-format prompt templates (Full/Compact/Local)
  - `exceptions.py`, `platform_exceptions.py`: Comprehensive error handling
  - `ssl_utils.py`: SSL certificate management for internal GitLab

**Development Workflow:**
- **Pre-commit Hooks**: Automatic code quality checks on commit (ruff, mypy, pytest, pymarkdown)
- **Coverage Requirements**: 75% minimum test coverage enforced in CI and pre-commit
- **Type Safety**: Strict mypy configuration with full annotation coverage
- **Modern Tooling**: uv for package management, ruff for linting/formatting
- **Structured Logging**: contextual logging for debugging and monitoring
- **YAML Configuration**: Team-shareable configuration via `.ai_review/config.yml`

### Local Git Workflow Details

**Key Dependencies:**
- **GitPython**: Core library for Git repository operations (requires Git binary)
- **pathlib**: Cross-platform path handling for repository URLs
- **asyncio**: Async Git operations to prevent blocking

**Local Review Process:**
1. **Repository Detection**: Auto-finds Git repo from current directory (searches parent dirs)
2. **Branch Analysis**: Gets current branch, handles detached HEAD states
3. **Merge Base Calculation**: Finds common ancestor with target branch (`origin/main` preferred)
4. **Branch Freshness Check**: Warns if local target branch is behind remote
5. **Diff Generation**: Creates diffs between current state and merge base
6. **Commit History**: Includes local commits for context
7. **Terminal Output**: Simplified markdown format optimized for terminal/file viewing

**Local-Specific Features:**
- No external API dependencies (works offline)
- Terminal-friendly output (no collapsible sections)
- File-based URLs for project context
- Smart handling of Git edge cases (detached HEAD, missing remotes)
- Integration with existing file filtering and AI provider selection

### Context Generator Tool Details

**AI Context Generator (`ai-generate-context`)**:
- **Intelligent Analysis**: Uses AI to understand codebase structure and purpose
- **Automatic Documentation**: Generates comprehensive project context files
- **Multi-Provider Support**: Works with Ollama, Gemini, Anthropic providers
- **Customizable Output**: Configurable output paths and formats
- **Integration Ready**: Outputs `.ai_review/context.md` for automatic inclusion in reviews

**Context Generation Process:**
1. **Repository Scanning**: Analyzes project structure, dependencies, and configuration
2. **AI Understanding**: Uses LLM to understand project purpose and architecture
3. **Context Synthesis**: Generates comprehensive documentation in markdown format
4. **Integration**: Context automatically included in subsequent code reviews

### Context7 Integration

**Context7 Service Integration** (v1.11.0+):
- **Official Library Documentation**: Fetches authoritative documentation from Context7 API
- **Intelligent Library Detection**: Auto-detects dependencies from project files and configuration
- **Enhanced Code Reviews**: Includes official documentation context in AI prompts for better accuracy
- **Configurable Priorities**: Specify important libraries for your project type (FastAPI, Django, etc.)
- **Smart Caching**: Session-based caching to minimize API calls during context generation

**Context7 Configuration**:
- **API Key Required**: Set `CONTEXT7_API_KEY` environment variable
- **Service URL**: https://context7.com (sign up for API access)
- **Integration Points**: Both `ai-generate-context` and `ai-code-review` tools support Context7
- **YAML Configuration**: Configure via `.ai_review/config.yml` with library priorities and settings
