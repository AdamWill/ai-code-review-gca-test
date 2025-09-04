# Developer Guide: AI Code Review

Guide for developers who want to understand, modify, or extend the AI Code Review project.

## 📑 Table of Contents

- [🏗️ Project Architecture](#️-project-architecture)
  - [High-Level Overview](#high-level-overview)
  - [Key Design Principles](#key-design-principles)
- [📁 Project Structure](#-project-structure)
  - [Key Files Explained](#key-files-explained)
- [🛠️ Technology Stack](#️-technology-stack)
  - [Core Dependencies](#core-dependencies)
  - [Development Tools](#development-tools)
- [🔧 Common Modification Scenarios](#-common-modification-scenarios)
  - [1. Adding a New Platform](#1-adding-a-new-platform-eg-bitbucket)
  - [2. Modifying AI Prompts](#2-modifying-ai-prompts)
  - [3. Adding New AI Providers](#3-adding-new-ai-providers)
  - [4. Adding Configuration Options](#4-adding-configuration-options)
  - [5. Modifying File Filtering](#5-modifying-file-filtering)
- [🧪 Development Workflow](#-development-workflow)
  - [Setup Development Environment](#setup-development-environment)
  - [Testing Strategy](#testing-strategy)
  - [Code Quality Checks](#code-quality-checks)
  - [Debugging Tips](#debugging-tips)
- [📚 Additional Resources](#-additional-resources)

## 🏗️ Project Architecture

### High-Level Overview

```
User/CI → CLI → Review Engine → AI Provider
               ↓              ↓
          Platform Client → GitLab/GitHub/Local Git
               ↓
          Configuration
               ↓
          Models & Data
```

The project follows a **layered architecture** with clear separation of concerns:

- **CLI Layer**: User interface and command-line argument handling
- **Business Logic**: Review orchestration and processing
- **Platform Layer**: GitLab, GitHub, and Local Git abstraction
- **Provider Layer**: AI model abstraction (Gemini, Anthropic, Ollama)
- **Data Layer**: Configuration, models, and platform-agnostic data structures
- **Utils**: Shared utilities, prompts, and exceptions

### Key Design Principles

- **Platform Abstraction**: Support for multiple platforms (GitLab, GitHub, Local Git)
- **Provider Abstraction**: Easy to add new AI providers via LangChain
- **Configuration-First**: All behavior configurable via environment variables
- **Type Safety**: Full type annotations and strict mypy checking
- **Testability**: Comprehensive mocking and testing infrastructure
- **Async-Ready**: Built for async operations where beneficial

## 📁 Project Structure

```
src/ai_code_review/
├── cli.py                      # 🎯 CLI entry point with multi-platform support
├── core/                       # 🧠 Core business logic
│   ├── base_platform_client.py # 🔧 Abstract platform client base
│   ├── gitlab_client.py        # 📡 GitLab API integration
│   ├── github_client.py        # 🐙 GitHub API integration
│   ├── local_git_client.py     # 🔍 Local Git integration
│   └── review_engine.py        # ⚙️  Platform-agnostic review orchestration
├── models/                     # 📋 Data models and validation
│   ├── config.py               # ⚙️  Multi-platform configuration with Pydantic
│   ├── platform.py             # 🌐 Platform-agnostic data models
│   └── review.py               # 📝 Review data structures
├── providers/                  # 🤖 AI provider implementations
│   ├── base.py                 # 🔧 Abstract base provider
│   ├── anthropic.py            # 🟠 Anthropic Claude implementation
│   ├── gemini.py               # 🟢 Google Gemini implementation
│   └── ollama.py               # 🔵 Ollama local LLM implementation
└── utils/                      # 🛠️  Shared utilities
    ├── exceptions.py           # ❌ Custom exceptions
    ├── platform_exceptions.py  # 🚫 Platform-specific exceptions
    ├── prompts.py              # 💬 LangChain prompt templates
    └── ssl_utils.py            # 🔒 SSL certificate utilities
```

### Key Files Explained

#### 🎯 `cli.py` - Command Line Interface

- Click-based CLI with **3 main workflows** support
- Handles `--local`, `--platform`, and posting options
- Configuration merging (env vars + CLI args)
- Entry point: `main()` function
- **Modify when:** Adding new CLI options or commands

#### ⚙️ `core/review_engine.py` - Main Business Logic

- Orchestrates the entire review process for **all 3 workflows**
- **Factory pattern** for platform clients (Local/GitLab/GitHub)
- Handles file filtering and diff processing
- Manages AI provider selection and invocation
- Token calculation and content optimization
- **Modify when:** Changing review workflow or adding new platforms

#### 🔧 `core/base_platform_client.py` - Platform Abstraction

- Abstract base class for **all platform types**
- Defines common interface: `get_pull_request_data()`, `post_review()`
- File filtering and content limit logic
- Platform-agnostic data model conversion
- **Implementations:** `GitLabClient`, `GitHubClient`, `LocalGitClient`

#### 📡 `core/gitlab_client.py` - GitLab Remote Client

- Implements remote GitLab MR analysis via API
- Fetches MR diffs, metadata, and commit information
- Posts review comments back to GitLab
- Handles GitLab API authentication with tokens
- **Modify when:** Adding GitLab-specific features or API fixes

#### 🐙 `core/github_client.py` - GitHub Remote Client

- Implements remote GitHub PR analysis via API
- Fetches PR diffs, metadata, and commit information
- Posts review comments to GitHub
- Handles GitHub API authentication with tokens
- **Modify when:** Adding GitHub-specific features or API fixes

#### 🔍 `core/local_git_client.py` - Local Git Client

- Implements **local Git review functionality**
- Uses `GitPython` for local repository operations (**requires Git binary**)
- Extracts diffs between local changes and target branch
- No authentication required - works with local repos only
- Cannot post reviews (returns mock success)
- **Prerequisites:** Git must be installed and accessible in PATH
- **Modify when:** Extending local Git functionality or diff processing

#### 💬 `utils/prompts.py` - AI Prompt Management

- LangChain prompt templates for **different review formats**
- **Full format:** Collapsible sections with MR summary (remote reviews)
- **Local format:** Simple, terminal-friendly output (local reviews)
- Helper functions for content extraction and formatting
- **Modify when:** Improving AI output quality or adding new formats

#### ⚙️ `models/config.py` - Configuration System

- Pydantic models for type-safe configuration
- **3 platform providers:** `GITLAB`, `GITHUB`, `LOCAL`
- Environment variable validation and Git repository detection
- AI provider and model configuration
- **Modify when:** Adding new configuration options or platforms

## 🛠️ Technology Stack

### Core Dependencies

```python
# CLI and HTTP
click>=8.1.0           # Modern CLI framework
aiohttp>=3.9.0         # Async HTTP client
httpx>=0.28.1          # Sync HTTP client (for Ollama)
python-gitlab>=4.0.0   # GitLab API client
pygithub>=2.1.0        # GitHub API client

# AI and LangChain
langchain>=0.2.0                # LLM framework
langchain-community>=0.2.0      # Community integrations
langchain-google-genai>=2.0.0   # Gemini integration
ollama>=0.2.0                   # Local LLM client
langchain-ollama>=0.2.0         # Ollama LangChain integration

# Data and Configuration
pydantic>=2.5.0          # Data validation and settings
pydantic-settings>=2.10.1 # Settings management
structlog>=23.2.0        # Structured logging

# Git Integration
GitPython>=3.1.40        # Local Git operations (requires Git binary installed)
```

### Development Tools

```python
# Code Quality
ruff>=0.1.0      # Linting and formatting
mypy>=1.7.0      # Type checking
bandit>=1.8.6    # Security linting

# Testing
pytest>=8.4.1           # Testing framework
pytest-asyncio>=1.1.0   # Async test support
pytest-mock>=3.14.1     # Mocking utilities
pytest-cov>=6.2.1       # Coverage reporting

# Development Workflow
pre-commit>=4.3.0  # Git hooks
uv                  # Package management
```

## 🔧 Common Modification Scenarios

### 1. Understanding the 3 Use Cases

The tool now supports **3 distinct workflows**:

1. **Local Reviews**: `LocalGitClient` - Reviews local Git changes using GitPython
2. **Remote Reviews**: `GitLabClient`/`GitHubClient` - Reviews existing MRs/PRs via API
3. **CI Integration**: Same as remote but with `--post-review` flag

All clients implement `BasePlatformClient` interface for consistency.

### 2. Adding a New Platform (e.g., Bitbucket)

**Files to modify:**

1. **Add Platform Provider** (`models/config.py`):

```python
class PlatformProvider(str, Enum):
    GITLAB = "gitlab"
    GITHUB = "github"
    LOCAL = "local"          # Already added!
    BITBUCKET = "bitbucket"  # NEW
```

1. **Create Platform Client** (`core/bitbucket_client.py`):

```python
class BitbucketClient(BasePlatformClient):
    """Bitbucket API client implementation."""

    async def get_pull_request_data(self) -> PullRequestData:
        # Implement Bitbucket API calls
        pass

    async def post_review(self, review_content: str) -> None:
        # Implement posting to Bitbucket
        pass
```

1. **Update Factory** (`core/review_engine.py`):

```python
def _create_platform_client(self) -> PlatformClientInterface:
    if self.config.platform_provider == PlatformProvider.BITBUCKET:
        return BitbucketClient(self.config)
    # ... other platforms
```

1. **Add Configuration** (`models/config.py`):

```python
# Bitbucket configuration
bitbucket_token: str | None = Field(default=None)
bitbucket_url: str = Field(default="https://api.bitbucket.org/2.0")
```

1. **Add Tests** (`tests/unit/test_bitbucket_client.py`):

Create comprehensive test suite following existing patterns.

### 3. Modifying AI Prompts

**File:** `src/ai_code_review/utils/prompts.py`

The prompt system supports **3 different output formats**:

1. **Full Format** (remote reviews): Collapsible sections with MR summary
2. **Compact Format** (remote reviews): No MR summary, technical focus
3. **Local Format** (local reviews): Terminal-friendly, no collapsible sections

#### Current Structure

```python
# Format templates for different review types
_FORMAT_EXAMPLE_FULL = """## AI Code Review
### 📋 MR Summary
<details><summary>Click to expand</summary>..."""

_FORMAT_EXAMPLE_COMPACT = """## AI Code Review
### 🔍 Detailed Code Review
Technical analysis without summary..."""

_FORMAT_EXAMPLE_LOCAL = """## 🔍 Code Analysis
Brief analysis for terminal display

## 📂 File Reviews
File-by-file review

## ✅ Summary
Key findings and recommendations"""

def create_system_prompt(include_mr_summary: bool = True, local_mode: bool = False) -> str:
    """System prompt with format-specific instructions"""
    # Different instructions for local vs remote reviews

def create_review_prompt(include_mr_summary: bool = True, local_mode: bool = False) -> ChatPromptTemplate:
    """User prompt template with format selection"""
    if local_mode:
        format_example = _FORMAT_EXAMPLE_LOCAL
    else:
        format_example = _FORMAT_EXAMPLE_FULL if include_mr_summary else _FORMAT_EXAMPLE_COMPACT

# Helper functions for modular content processing
def _extract_diff_content(input_data: dict[str, Any]) -> str:
def _create_language_hint_section(input_data: dict[str, Any]) -> str:
def _create_project_context_section(input_data: dict[str, Any]) -> str:
```

#### How to Modify Prompts

##### Example 1: Add new output format

```python
# 1. Create new format template
_FORMAT_EXAMPLE_SECURITY = """## 🔒 Security Review
### 🚨 Critical Security Issues
High-priority vulnerabilities requiring immediate attention

### ⚠️ Security Considerations
Medium-priority security improvements

### ✅ Security Recommendations
Best practices and preventive measures"""

# 2. Update system prompt function
def create_system_prompt(include_mr_summary: bool = True, local_mode: bool = False, security_focus: bool = False) -> str:
    if security_focus:
        return """You are a senior security engineer focused on code security.
        Prioritize identifying vulnerabilities, security anti-patterns..."""
    # ... existing logic

# 3. Update review prompt function
def create_review_prompt(include_mr_summary: bool = True, local_mode: bool = False, security_focus: bool = False) -> ChatPromptTemplate:
    if security_focus:
        format_example = _FORMAT_EXAMPLE_SECURITY
    elif local_mode:
        format_example = _FORMAT_EXAMPLE_LOCAL
    # ... existing logic
```

##### Example 2: Add new helper function

```python
def _create_security_context_section(input_data: dict[str, Any]) -> str:
    """Create security context section if security data is provided."""
    security_context = input_data.get("security_context")
    if security_context and security_context.strip():
        return f"## 🔒 Security Context\n{security_context}"
    return ""

# Add to _build_chain_inputs()
def _build_chain_inputs(include_mr_summary: bool, local_mode: bool) -> dict[str, Any]:
    return {
        "system_prompt": _create_system_prompt_func(include_mr_summary, local_mode),
        "security_context_section": _create_security_context_section,  # NEW
        # ... existing helpers
    }
```

**Testing Prompt Changes:**

```bash
# Test with dry run
ai-code-review group/project 123 --dry-run

# Test with real AI but no posting
ai-code-review group/project 123

# Test specific scenarios
ai-code-review group/project 123 --language-hint python --exclude-files "test_*"

# Test review format options
ai-code-review group/project 123 --no-mr-summary --dry-run  # Short format
ai-code-review group/project 123 --dry-run                  # Full format (default)
```

### 4. Review Format Configuration

**Files:** `src/ai_code_review/models/config.py`, `src/ai_code_review/cli.py`, `src/ai_code_review/utils/prompts.py`

The project supports **3 review formats** optimized for different workflows:

#### Available Formats

**1. Full Format (Remote Reviews - Default):**
- 📋 **MR Summary**: High-level change overview with collapsible sections
- 📝 **Detailed Code Review**: Technical analysis
- ✅ **Summary**: Key findings and recommendations

**2. Compact Format (Remote Reviews - `--no-mr-summary`):**
- 📝 **Detailed Code Review**: Technical analysis (main focus)
- ✅ **Summary**: Key findings and recommendations

**3. Local Format (Local Reviews - `--local`):**
- 🔍 **Code Analysis**: Brief technical analysis
- 📂 **File Reviews**: File-by-file review
- ✅ **Summary**: Key findings and recommendations
- **No collapsible sections** - optimized for terminal display

#### Configuration Methods

**CLI Flags:**
```bash
# Local format (terminal-friendly)
ai-code-review --local

# Remote formats
ai-code-review group/project 123                  # Full format (default)
ai-code-review group/project 123 --no-mr-summary  # Compact format
```

**Environment Variable:**
```bash
export INCLUDE_MR_SUMMARY=false  # Enable compact format for remote reviews
export INCLUDE_MR_SUMMARY=true   # Enable full format (default)
```

**Programmatic Configuration:**
```python
from ai_code_review.models.config import Config, PlatformProvider

# Local format (automatic when using LOCAL platform)
config = Config(platform_provider=PlatformProvider.LOCAL)

# Remote formats
config = Config(include_mr_summary=False)  # Compact
config = Config()                          # Full format (default)
```

#### Implementation Details

The format configuration affects:

1. **Prompt Templates** (`utils/prompts.py`):
   ```python
   # Constants for all 3 formats
   _FORMAT_EXAMPLE_FULL = """## AI Code Review
   ### 📋 MR Summary
   ### Detailed Code Review
   ### ✅ Summary"""

   _FORMAT_EXAMPLE_COMPACT = """## AI Code Review
   ### Detailed Code Review
   ### ✅ Summary"""

   _FORMAT_EXAMPLE_LOCAL = """## 🔍 Code Analysis
   ### 📂 File Reviews
   ### ✅ Summary"""

   # Format selection logic
   def create_review_prompt(include_mr_summary: bool = True, local_mode: bool = False) -> ChatPromptTemplate:
       if local_mode:
           format_example = _FORMAT_EXAMPLE_LOCAL
       else:
           format_example = _FORMAT_EXAMPLE_FULL if include_mr_summary else _FORMAT_EXAMPLE_COMPACT
   ```

2. **System Prompts** (conditional based on format and mode)
3. **Mock Reviews** (format-aware for dry-run testing)

#### Testing Format Options

```bash
# Test all 3 formats
ai-code-review --local --dry-run                           # Local format
ai-code-review group/project 123 --dry-run                 # Full remote format
ai-code-review group/project 123 --dry-run --no-mr-summary # Compact remote format

# Integration testing
uv run pytest tests/unit/test_prompts.py -k "local_mode" -v
uv run pytest tests/unit/test_prompts.py -k "mr_summary" -v
uv run pytest tests/unit/test_review_engine.py -k "format" -v
```

### 5. Project Context Integration

**Files:** `src/ai_code_review/core/review_engine.py`, `src/ai_code_review/models/config.py`, `src/ai_code_review/cli.py`

The **Project Context** feature allows AI reviews to understand project-specific patterns, architecture, and "gotchas".

#### How It Works

1. **Configuration** (`models/config.py`):
   ```python
   enable_project_context: bool = Field(
       default=True,
       description="Enable loading project context from .ai_review/project.md file",
   )
   project_context_file: str = Field(
       default=".ai_review/project.md",
       description="Path to project context file (relative to repository root)",
   )
   ```

2. **CLI Integration** (`cli.py`):
   ```python
   @click.option(
       "--project-context/--no-project-context",
       default=None,
       help="Enable/disable loading project context",
   )
   ```

3. **Context Loading** (`core/review_engine.py`):
   ```python
   def _load_project_context_file(self) -> str | None:
       """Load project context from configured project context file."""
       context_file_path = self.config.project_context_file
       # Safe file loading with error handling...

   def _get_project_context(self, pr_data: PullRequestData | None = None) -> str:
       """Get project context for AI review."""
       if self.config.enable_project_context:
           project_context_content = self._load_project_context_file()
           if project_context_content:
               context_parts.append("**Project Context:**")
               context_parts.append(project_context_content)
   ```

4. **Prompt Integration** (`utils/prompts.py`):
   ```python
   def _create_project_context_section(input_data: dict[str, Any]) -> str:
       """Create project context section if context is provided."""
       context = input_data.get("context")  # From _get_project_context()
       if context and context.strip():
           return f"## Project Context\n{context}"
       return ""
   ```

#### Key Design Decisions

- **Default Enabled**: Automatically loads if `.ai_review/project.md` exists
- **Safe Loading**: Graceful fallback if file doesn't exist or can't be read
- **Environment Control**: Can be disabled via `ENABLE_PROJECT_CONTEXT=false`
- **CLI Override**: Explicit control with `--project-context`/`--no-project-context`
- **Context Position**: Injected between language hint and diff content in prompts

#### Extending the Feature

**Add new context sources:**
```python
def _load_additional_context(self) -> str:
    """Load context from other sources (README.md, etc.)"""
    # Implementation for README.md, .cursorrules, etc.

def _get_project_context(self, mr_data: MergeRequestData | None = None) -> str:
    context_parts = []

    if self.config.enable_project_context:
        # Existing .ai_review/project.md loading
        project_context = self._load_project_context_file()
        if project_context:
            context_parts.append(project_context)

        # NEW: Additional context sources
        additional_context = self._load_additional_context()
        if additional_context:
            context_parts.append(additional_context)
```

**Add external context URLs:**
```python
enable_external_context: bool = Field(default=False)
external_context_url: str | None = Field(default=None)

async def _fetch_external_context(self) -> str | None:
    """Fetch context from external URL (docs site, wiki, etc.)"""
    if not self.config.enable_external_context or not self.config.external_context_url:
        return None
    # HTTP fetch implementation...
```

**Use custom context file paths:**
```python
# Via environment variable
PROJECT_CONTEXT_FILE=docs/ai-context.md

# Via CLI (future implementation)
ai-code-review --context-file docs/ai-context.md project/123

# Via config object
config = Config(
    gitlab_token="token",
    project_context_file="custom/path/context.md"
)
```

#### Testing

The feature has comprehensive test coverage in `tests/unit/test_review_engine.py`:

- ✅ Context loading (file exists, not exists, empty)
- ✅ Configuration integration (enabled/disabled)
- ✅ CLI flag handling
- ✅ Integration with review generation

Run specific tests:
```bash
uv run pytest tests/unit/test_review_engine.py -k "project_context" -v
```

### 4. Modifying File Filtering

**File:** `src/ai_code_review/models/config.py`

Current filtering happens in `get_default_exclude_patterns()`:

```python
def get_default_exclude_patterns() -> list[str]:
    return [
        "*.lock",              # Lockfiles
        "*.min.js",            # Minified files
        "node_modules/**",     # Dependencies
        "__pycache__/**",      # Python cache
        "dist/**",             # Build output
        # Add new patterns here
        "*.generated.ts",      # Generated TypeScript
        "**/migrations/**",    # Database migrations
        "coverage/**",         # Coverage reports
    ]
```

#### Step 2: Update Configuration

```python
# src/ai_code_review/models/config.py
class AIProvider(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"  # Add new provider

# Update default model mapping if needed
def get_default_model_for_provider(provider: AIProvider) -> str:
    defaults = {
        AIProvider.OLLAMA: "qwen2.5-coder:7b",
        AIProvider.GEMINI: "gemini-2.5-pro",
        AIProvider.ANTHROPIC: "claude-sonnet-4-20250514",  # Already implemented!
    }
    return defaults.get(provider, "gemini-2.5-pro")
```

#### Step 3: Update Provider Factory

```python
# src/ai_code_review/core/review_engine.py
def _create_ai_provider(self) -> BaseAIProvider:
    if self.config.ai_provider == AIProvider.OLLAMA:
        from ai_code_review.providers.ollama import OllamaProvider
        return OllamaProvider(self.config)
    elif self.config.ai_provider == AIProvider.GEMINI:
        from ai_code_review.providers.gemini import GeminiProvider
        return GeminiProvider(self.config)
    elif self.config.ai_provider == AIProvider.ANTHROPIC:  # Add new case
        from ai_code_review.providers.anthropic import AnthropicProvider
        return AnthropicProvider(self.config)
```

#### Step 4: Add Tests

```python
# tests/unit/test_anthropic_provider.py
def test_anthropic_provider_creation(test_config):
    test_config.ai_provider = AIProvider.ANTHROPIC
    test_config.ai_api_key = "test-key"

    provider = AnthropicProvider(test_config)
    assert provider.is_available() == True
```

### 5. Adding Configuration Options

**File:** `src/ai_code_review/models/config.py`

#### Add New Configuration Field

```python
class Config(BaseSettings):
    # Existing fields...

    # Add new field with validation
    custom_timeout: int = Field(
        default=30,
        description="Custom operation timeout in seconds",
        gt=0,
        le=300,  # Max 5 minutes
    )

    # Real examples from the project:
    include_mr_summary: bool = Field(
        default=True,
        description="Include MR Summary section in reviews"
    )

    target_branch: str = Field(
        default="main",
        description="Target branch for local reviews"
    )

    # Add validation if needed
    @field_validator("custom_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 10:
            logger.warning("Timeout too low, setting minimum of 10 seconds")
            return 10
        return v
```

#### Update CLI Arguments

```python


**Testing File Filtering:**

```bash
# Test local filtering
ai-code-review --local --exclude-files "*.test.*,docs/**"

# Test remote filtering
ai-code-review group/project 123 --exclude-files "*.test.*" --exclude-files "docs/**"

# Test with different file limits
ai-code-review --local --max-files 5 --max-file-context 1000
```

## 🧪 Development Workflow

### Setup Development Environment

```bash
# Clone and setup
git clone https://gitlab.com/redhat/edge/ci-cd/ai-code-review.git
cd ai-code-review

# Install with development dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run all quality checks
uv run ruff check . --fix
uv run ruff format .
uv run mypy src/
uv run pytest
```

### Testing Strategy

#### Unit Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_prompts.py -v

# Test specific function
uv run pytest tests/unit/test_prompts.py::test_create_review_chain -v
```

#### Integration Testing

```bash
# Test local reviews (no tokens needed!)
ai-code-review --local --dry-run             # Mock local review
ai-code-review --local                       # Real local review with AI

# Test remote reviews
GITLAB_TOKEN=your_token ai-code-review group/project 123 --dry-run
GITHUB_TOKEN=your_token ai-code-review --platform github owner/repo 456 --dry-run

# Test with Ollama locally
ollama serve  # In another terminal
ai-code-review --local --ai-provider ollama  # Local review with local AI
ai-code-review group/project 123 --ai-provider ollama  # Remote review with local AI

# Test health checks
AI_API_KEY=your_key ai-code-review --health-check
```

### Code Quality Checks

Pre-commit runs automatically, but you can run manually:

```bash
# Format and lint
uv run ruff check . --fix
uv run ruff format .

# Type checking
uv run mypy src/

# Security scanning
uv run bandit -r src/

# Run all pre-commit checks
uv run pre-commit run --all-files
```

### Debugging Tips

#### Enable Debug Logging

```bash
# Local review debugging
LOG_LEVEL=DEBUG ai-code-review --local

# Remote review debugging
LOG_LEVEL=DEBUG ai-code-review group/project 123

# In code
import structlog
logger = structlog.get_logger()
logger.debug("Debug message", extra_data="value")
```

#### Test Individual Components

```python
# Test configuration
from ai_code_review.models.config import Config
config = Config()
print(config.ai_provider, config.ai_model)

# Test AI provider
from ai_code_review.providers.gemini import GeminiProvider
provider = GeminiProvider(config)
print(provider.is_available())

# Test prompts
from ai_code_review.utils.prompts import create_review_chain
chain = create_review_chain(provider.client)
result = chain.invoke({"diff": "test diff", "language": "python"})
```

#### Common Issues

**"Module not found" errors:**
```bash
# Make sure you're in the right environment
which python
# Should show: .../ai-code-review/.venv/bin/python

# Reinstall in development mode
uv sync --dev
```

**Type checking errors:**
```bash
# Run mypy on specific file
uv run mypy src/ai_code_review/providers/gemini.py

# Ignore specific error (last resort)
# type: ignore[error-code]
```

## 📚 Additional Resources

### Project Documentation

- **User Guide**: `docs/user-guide.md` - How to use the tool
- **Specifications**: `SPECS.md` - Detailed requirements and architecture
- **README**: `README.md` - Quick start and overview

### External Documentation

- **LangChain**: <https://python.langchain.com/docs/> - AI framework documentation
- **Pydantic**: <https://docs.pydantic.dev/latest/> - Data validation library
- **Click**: <https://click.palletsprojects.com/> - CLI framework
- **GitLab API**: <https://docs.gitlab.com/ee/api/> - GitLab REST API reference

### Getting Help

- **Issues**: <https://gitlab.com/redhat/edge/ci-cd/ai-code-review/-/issues>
- **Discussions**: Use GitLab Issues for questions and discussions
- **Code Review**: All changes require MR review before merging

---

**Happy coding!** 🚀
