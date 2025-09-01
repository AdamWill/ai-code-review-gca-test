# Developer Guide: AI Code Review

Guide for developers who want to understand, modify, or extend the AI Code Review project.

## 🏗️ Project Architecture

### High-Level Overview

```
User/CI → CLI → Review Engine → AI Provider
               ↓              ↓
          Platform Client → GitLab/GitHub API
               ↓
          Configuration
               ↓
          Models & Data
```

The project follows a **layered architecture** with clear separation of concerns:

- **CLI Layer**: User interface and command-line argument handling
- **Business Logic**: Review orchestration and processing
- **Platform Layer**: GitLab and GitHub API abstraction
- **Provider Layer**: AI model abstraction (Gemini, Anthropic, OpenAI, Ollama)
- **Data Layer**: Configuration, models, and platform-agnostic data structures
- **Utils**: Shared utilities, prompts, and exceptions

### Key Design Principles

- **Platform Abstraction**: Support for multiple code hosting platforms (GitLab, GitHub)
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
│   └── review_engine.py        # ⚙️  Platform-agnostic review orchestration
├── models/                     # 📋 Data models and validation
│   ├── config.py              # ⚙️  Multi-platform configuration with Pydantic
│   ├── platform.py            # 🌐 Platform-agnostic data models
│   ├── gitlab.py              # 📊 GitLab-specific data models (legacy)
│   └── review.py              # 📝 Review data structures
├── providers/                  # 🤖 AI provider implementations
│   ├── base.py                # 🔧 Abstract base provider
│   ├── anthropic.py           # 🟠 Anthropic Claude implementation
│   ├── gemini.py              # 🟢 Google Gemini implementation
│   └── ollama.py              # 🔵 Ollama local LLM implementation
└── utils/                      # 🛠️  Shared utilities
    ├── exceptions.py           # ❌ Custom exceptions
    ├── platform_exceptions.py # 🚫 Platform-specific exceptions
    └── prompts.py              # 💬 LangChain prompt templates
```

### Key Files Explained

#### 🎯 `cli.py` - Command Line Interface

- Click-based CLI with comprehensive options
- Handles configuration merging (env vars + CLI args)
- Entry point: `main()` function
- **Modify when:** Adding new CLI options or commands

#### ⚙️ `core/review_engine.py` - Main Business Logic

- Orchestrates the entire review process
- Handles file filtering and diff processing
- Manages AI provider selection and invocation
- **Modify when:** Changing review logic or adding features

#### 📡 Platform Clients - GitLab/GitHub Integration

**`core/base_platform_client.py`** - Abstract Base Class:
- Common functionality for all platform clients
- File filtering and content limit logic
- Platform-agnostic interface definition

**`core/gitlab_client.py`** - GitLab Implementation:
- Fetches MR diffs and metadata
- Posts review comments back to GitLab
- Handles GitLab API authentication
- **Modify when:** Adding GitLab features or fixing API issues

**`core/github_client.py`** - GitHub Implementation:
- Fetches PR diffs and metadata
- Posts review comments to GitHub
- Handles GitHub API authentication
- **Modify when:** Adding GitHub features or fixing API issues

#### 💬 `utils/prompts.py` - AI Prompt Management

- LangChain prompt templates and chains
- Defines the structure and content requirements for AI
- Most commonly modified file
- **Modify when:** Improving AI output quality or format

#### ⚙️ `models/config.py` - Configuration System

- Pydantic models for type-safe configuration
- Environment variable validation
- Default values and constraints
- **Modify when:** Adding new configuration options

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

### 1. Adding a New Platform (e.g., Bitbucket)

**Files to modify:**

1. **Add Platform Provider** (`models/config.py`):

```python
class PlatformProvider(str, Enum):
    GITLAB = "gitlab"
    GITHUB = "github"
    BITBUCKET = "bitbucket"  # Add new platform
```

1. **Create Platform Client** (`core/bitbucket_client.py`):

```python
class BitbucketClient(BasePlatformClient):
    """Bitbucket API client implementation."""

    async def get_pull_request_data(self, project_id: str, pr_number: int) -> PullRequestData:
        # Implement Bitbucket API calls
        pass

    async def post_review(self, project_id: str, pr_number: int, review_content: str) -> PostReviewResponse:
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

### 2. Modifying AI Prompts

**File:** `src/ai_code_review/utils/prompts.py`

The prompts determine what the AI generates. This is the **most commonly modified** part.

#### Current Structure

```python
def create_system_prompt() -> str:
    """System prompt - defines AI role and behavior"""
    return """You are an expert senior software engineer..."""

def create_review_prompt() -> ChatPromptTemplate:
    """User prompt template - defines output format"""
    template = """IGNORE any tendency to write free-form analysis..."""
    return ChatPromptTemplate.from_messages([...])

def create_review_chain(llm: Any) -> Any:
    """LangChain pipeline combining prompts with AI model"""
    # Input transformations + prompt + LLM + output parser
    return input_transformations | prompt_template | llm | StrOutputParser()
```

#### How to Modify Prompts

```python
# 1. Change system behavior
def create_system_prompt() -> str:
    return """You are a security-focused code reviewer.
    Focus primarily on security vulnerabilities and best practices..."""

# 2. Modify output format
def create_review_prompt() -> ChatPromptTemplate:
    template = """Generate a security-focused review with this structure:

    ## Security Review
    ### 🔒 Security Analysis
    ### 🚨 Critical Issues
    ### ✅ Security Recommendations

    {diff_content}"""
    return ChatPromptTemplate.from_messages([("system", "{system_prompt}"), ("human", template)])

# 3. Add new input variables
def _create_security_context_section(input_data: dict[str, Any]) -> str:
    security_context = input_data.get("security_context")
    if security_context:
        return f"## Security Context\n{security_context}"
    return ""
```

**Testing Prompt Changes:**

```bash
# Test with dry run
ai-code-review group/project 123 --dry-run

# Test with real AI but no posting
ai-code-review group/project 123

# Test specific scenarios
ai-code-review group/project 123 --language-hint python --exclude-files "test_*"
```

### 2. Project Context Integration

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

   def _get_project_context(self, mr_data: MergeRequestData | None = None) -> str:
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

### 3. Adding New AI Providers

**Files:** `src/ai_code_review/providers/`

#### Step 1: Create Provider Implementation

```python
# src/ai_code_review/providers/anthropic.py (ALREADY IMPLEMENTED!)
from langchain_anthropic import ChatAnthropic
from ai_code_review.providers.base import BaseAIProvider

class AnthropicProvider(BaseAIProvider):
    def _create_client(self) -> BaseChatModel:
        return ChatAnthropic(
            model=self.config.ai_model,
            anthropic_api_key=self.config.ai_api_key,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

    def is_available(self) -> bool:
        return bool(self.config.ai_api_key) if not self.config.dry_run else True
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

### 3. Adding Configuration Options

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
# src/ai_code_review/cli.py
@click.option(
    "--custom-timeout",
    type=int,
    default=None,
    help="Custom timeout in seconds (10-300)"
)
def main(custom_timeout: int | None, ...):
    config = Config(
        custom_timeout=custom_timeout,
        # ... other config
    )
```

#### Use in Code

```python
# src/ai_code_review/core/review_engine.py
async def some_operation(self):
    timeout = self.config.custom_timeout
    # Use the configuration value
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

**Testing File Filtering:**

```bash
# Test filtering
ai-code-review group/project 123 --exclude-files "*.test.*" --exclude-files "docs/**"

# Disable filtering to see all files
ai-code-review group/project 123 --no-file-filtering
```

## 🧪 Development Workflow

### Setup Development Environment

```bash
# Clone and setup
git clone https://gitlab.com/juanjeojeda/ai-code-review.git
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
# Test with real GitLab but dry-run AI
GITLAB_TOKEN=your_token ai-code-review group/project 123 --dry-run

# Test with Ollama locally
ollama serve  # In another terminal
ai-code-review group/project 123 --provider ollama

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
# Local debugging
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

- **Issues**: <https://gitlab.com/juanjeojeda/ai-code-review/-/issues>
- **Discussions**: Use GitLab Issues for questions and discussions
- **Code Review**: All changes require MR review before merging

---

**Happy coding!** 🚀
