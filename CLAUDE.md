# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ Critical Design Decisions (READ FIRST)

### 1. Configuration System: Never Use default_factory with Field References
**Problem** (commit `8fbf91b`): `default_factory` executes at field definition time, breaking the layered config system (CLI > Env > File > Defaults).

❌ **WRONG**:
```python
ai_model: str = Field(default_factory=lambda: get_default_model_for_provider(DEFAULT_AI_PROVIDER))
```

✅ **CORRECT**:
```python
ai_model: str | None = Field(default=None)

def get_ai_model(self) -> str:
    return self.ai_model or get_default_model_for_provider(self.ai_provider)
```

**Rule**: All code must use `config.get_ai_model()`, never `config.ai_model`.

### 2. HTTP Client: Use httpx, Not aiohttp
**Decision**: `httpx` is the standard HTTP client (both sync and async).

**Why**:
- Single dependency for sync + async operations
- Used in: Ollama health checks, team context loading, SSL downloads
- Synchronous `httpx.get()` is acceptable for initialization operations

**Do NOT**:
- Suggest converting `httpx` to `aiohttp` for "consistency"
- Make initialization I/O async unnecessarily
- Add dual HTTP dependencies without strong justification

### 3. Async vs Sync I/O
**Rule**: Only use async for hot-path operations (inside loops, repeated calls).

**Acceptable Synchronous**:
- Configuration loading at startup
- Health checks (once per execution)
- Context file loading (once per review)

**Require Asynchronous**:
- Platform API calls (GitLab/GitHub)
- LLM invocations (`.ainvoke()`)
- Operations inside loops

## Essential Commands

### Development Setup

**Install Dependencies:**
```bash
uv sync --dev                    # Install all dependencies including GitPython
uv run pre-commit install        # Setup quality checks
```

**Configure Environment** (choose based on workflow):
```bash
# Option 1: Environment variables
cp env.example .env

# Option 2: YAML configuration (team-shareable, v1.7.0+)
mkdir -p .ai_review && cp .ai_review/config.yml.example .ai_review/config.yml
```

**Required Tokens** (edit .env or config.yml):
- `GITLAB_TOKEN`: For GitLab MRs (not needed for `--local`)
- `GITHUB_TOKEN`: For GitHub PRs (not needed for `--local`)
- `AI_API_KEY`: For cloud providers (not needed for `--provider ollama`)
- **LOCAL workflow**: Only needs Git repository (no tokens required)

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

# NEW v1.15.0: Team context and synthesis options
ai-code-review group/project 123 --team-context https://company.com/standards.md
ai-code-review --local --team-context ../org-standards.md
ENABLE_REVIEW_SYNTHESIS=false ai-code-review --post      # Skip comment synthesis

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

An **AI-powered CLI tool** for automated code reviews supporting:
- **GitLab Merge Requests** & **GitHub Pull Requests**
- **Local Git changes** (offline-capable)
- **Three workflows**: Local development, Remote analysis, CI/CD automation

**Key Features (v1.15.0)**:
- **Two-Phase Review**: Comment synthesis (fast model) + main review (quality model)
- **Team Context**: Organization-wide standards via local files or remote URLs
- **Adaptive Context**: Auto-expands window size based on diff size (16K → 24K)
- **Multiple Providers**: Ollama (local), Gemini (default cloud), Anthropic (quality)

### Core Design Principles

**1. Multi-Modal AI Strategy**:
- Local Dev: Ollama + `qwen2.5-coder:7b` (free, no API keys)
- Production/CI: Gemini `gemini-3-pro-preview` (default)
- Synthesis: Fast models (Gemini Flash, Claude Haiku) for comment preprocessing
- Quality: Claude Sonnet 4 for critical reviews

**2. Intelligent Context Management**:
- Hierarchy: team_context > project_context > commit_history
- Smart sizing: 16K standard, auto-expands to 24K for large diffs
- File filtering: Auto-excludes lockfiles, build artifacts, minified files
- Review synthesis: Preprocesses previous comments to avoid repetition

**3. Unified Output Generation**:
- Single LLM call for efficiency
- Format adapts to workflow: Full (remote/CI), Compact, Local (terminal)
- Markdown-compatible for platform display

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

**1. Configuration System (`models/config.py`)** ⭐:
- Pydantic-based with layered priority
- Smart validation with helpful error messages
- **Critical**: Must use None + getter pattern for interdependent fields

**2. Review Engine (`core/review_engine.py`)** ⭐:
- Two-phase review: synthesis + main review (v1.15.0+)
- Factory pattern for platform/provider creation
- Context hierarchy: team > project > commits
- Adaptive context windows, intelligent skip logic

**3. AI Providers (`providers/`)** ⭐:
- LangChain-based abstraction (Ollama, Gemini, Anthropic)
- Model override support for synthesis vs main review
- Health checks use `httpx` (sync/async OK)

**4. Platform Clients (`core/`)** ⭐:
- GitLab: python-gitlab, SSL support, discussion threads
- GitHub: PyGithub, Actions integration, PR comments
- Local: GitPython, offline-capable, terminal output

**5. Prompt Management (`utils/prompts.py`)**:
- LangChain templates with LCEL (prompt | model)
- Two chains: synthesis (fast) + review (main)
- Dynamic context injection

### Configuration Architecture

**Priority Order**: `CLI args > Environment vars > Config file > Defaults`

**Configuration Methods** (choose one or combine):
1. CLI arguments: `--provider gemini --model gemini-3-pro-preview`
2. Environment variables: `AI_PROVIDER=gemini AI_MODEL=gemini-3-pro-preview`
3. YAML config file: `.ai_review/config.yml` (team-shareable)
4. Defaults: Auto-selected per provider

**Common Configurations**:

```bash
# Local Git + Ollama (no tokens, works offline)
ai-code-review --local --provider ollama

# Remote + Cloud AI (tokens required)
GITLAB_TOKEN=glpat_xxx AI_API_KEY=your_key ai-code-review group/project 123

# CI/CD with synthesis and team context (v1.15.0)
AI_PROVIDER=gemini
AI_API_KEY=your_key
TEAM_CONTEXT_FILE=https://company.com/standards.md
ENABLE_REVIEW_SYNTHESIS=true
# In .gitlab-ci.yml or GitHub Actions:
ai-code-review --post

# Context generation with Context7
CONTEXT7_API_KEY=ctx7_xxx ai-generate-context --enable-context7
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

### Development Workflow

**Testing**: Mock external dependencies, 75% coverage minimum, `@pytest.mark.asyncio` for async code  
**Quality Checks**: Pre-commit hooks (ruff, mypy, pytest), strict type annotations  
**Tools**: uv (packages), ruff (lint/format), pytest (testing)  
**Config**: YAML-based via `.ai_review/config.yml`

## Common Review Issues & Solutions

### ❌ Configuration Pitfalls

**Issue 1: Using `default_factory` with field references** (commit `8fbf91b`)
```python
# NEVER DO THIS
ai_model: str = Field(default_factory=lambda: get_default(...))

# ALWAYS DO THIS
ai_model: str | None = Field(default=None)
def get_ai_model(self) -> str:
    return self.ai_model or get_default_model_for_provider(self.ai_provider)
```
**Why**: Breaks layered config - causes provider/model mismatches.

**Issue 2: Validators that set values**
- Validators should only validate, not set defaults
- Setting values in validators bypasses CLI/env overrides
- Test with direct `Config(field=value)` instantiation

### ❌ HTTP Client Confusion

**Issue**: Suggesting httpx → aiohttp conversion for "consistency"

**Correct Approach**:
- Use `httpx` as standard (sync + async in one library)
- Keep existing `aiohttp` where it exists (platform clients)
- Don't convert unless there's a performance need
- Sync `httpx.get()` acceptable for initialization

**Where httpx is used**: Ollama health checks, team context loading, SSL downloads

### ❌ Unnecessary Async Conversion

**Not everything needs to be async**:
- Config loading at startup → OK to be sync
- Health checks (once per execution) → OK to be sync
- Context file loading (once per review) → OK to be sync

**Must be async**:
- Platform API calls (GitLab/GitHub)
- LLM invocations (`.ainvoke()`)
- Operations inside loops

### ❌ Test Mocking Issues

**When updating to async**:
- Remember to update ALL tests that call the method
- Use `@pytest.mark.asyncio` decorator
- Mock with `AsyncMock` for async operations
- Properly configure async context managers:
  ```python
  mock_cm = Mock()
  mock_cm.__aenter__ = AsyncMock(return_value=mock_obj)
  mock_cm.__aexit__ = AsyncMock(return_value=None)
  ```

### Local Git Workflow (Offline Mode)

**Key Points**:
- Uses GitPython (requires Git binary)
- Works offline (no platform tokens needed)
- Compares current changes vs target branch (default: main)
- Terminal-friendly output format

**Process**: Auto-detect repo → Calculate merge base → Generate diffs → Format for terminal

## New Features (v1.15.0)

### 1. Intelligent Review Context with Comment Synthesis

**Problem Solved**: Avoid repeating suggestions already discussed in previous reviews.

**How It Works**:
- Fetches up to 30 recent comments/reviews from platform API
- Filters bot comments and system notes
- Fast model synthesizes key insights (~2000 tokens)
- Main review uses synthesis as context
- Skips automatically when no comments exist

**Configuration**:
```bash
ENABLE_REVIEW_CONTEXT=true          # Fetch previous comments (default)
ENABLE_REVIEW_SYNTHESIS=true        # LLM synthesis (default)
SYNTHESIS_MODEL=gemini-2.5-flash    # Fast model override (optional)
MAX_COMMENTS_TO_FETCH=30            # API limit (default)
```

**Models Used**:
- Synthesis: Gemini Flash, Claude Haiku, same as main for Ollama
- Main: Gemini 3 Pro Preview, Claude Sonnet 4, Qwen 2.5 Coder

### 2. Team/Organization Context Support

**Problem Solved**: Share coding standards across multiple projects.

**How It Works**:
- Priority: team_context > project_context > commit_history
- Supports local file paths and HTTP/HTTPS URLs
- Remote URLs fetched at startup (no caching)
- Synchronous loading acceptable (happens once)

**Configuration**:
```bash
# CLI option
ai-code-review group/project 123 --team-context https://company.com/standards.md

# Environment variable
TEAM_CONTEXT_FILE=https://company.com/review-guidelines.md

# YAML config (.ai_review/config.yml)
team_context_file: ../shared/team-standards.md
```

**Use Cases**:
- Organization-wide coding standards
- Shared security guidelines
- Common architectural patterns
- Language-specific best practices

### Context Generator Tool

Generates intelligent project documentation for better AI code reviews.

**Usage**:
```bash
ai-generate-context                              # Creates .ai_review/context.md
ai-generate-context --enable-context7            # With official library docs
ai-generate-context --provider ollama            # Use local AI
```

**Features**:
- Analyzes project structure, dependencies, and configuration
- Uses AI to understand project purpose and architecture
- Generates comprehensive markdown documentation
- Auto-included in subsequent reviews via `project_context_file`

**Context7 Integration** (v1.13.0+):
- Fetches official library documentation from Context7 API
- Requires `CONTEXT7_API_KEY` environment variable
- Auto-detects dependencies from project files
- Enhances review accuracy with authoritative docs
