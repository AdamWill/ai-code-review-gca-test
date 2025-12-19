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
- [🚀 Complete Diff Fetching System](#-complete-diff-fetching-system)
  - [Overview](#overview)
  - [Architecture](#architecture)
  - [Key Components](#key-components)
  - [Performance Optimizations](#performance-optimizations)
  - [Testing Strategy](#testing-strategy-1)
  - [Extending the System](#extending-the-system)
- [🔧 Common Modification Scenarios](#-common-modification-scenarios)
  - [1. Adding a New Platform](#1-adding-a-new-platform-eg-bitbucket)
  - [2. Modifying AI Prompts](#2-modifying-ai-prompts)
  - [3. Adding New AI Providers](#3-adding-new-ai-providers)
  - [4. Adding Configuration Options](#4-adding-configuration-options)
  - [5. Modifying File Filtering](#5-modifying-file-filtering)
  - [6. Adaptive Context Size Management](#6-adaptive-context-size-management)
  - [7. Project Context Integration](#7-project-context-integration)
  - [8. Extending Skip Review Mechanism](#8-extending-skip-review-mechanism)
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

- **Multi-layered Configuration**: YAML files + Environment variables + CLI arguments
- **YAML Configuration Support**: Auto-detects `.ai_review/config.yml` with custom path support
- Pydantic models for type-safe configuration with comprehensive validation
- **3 platform providers:** `GITLAB`, `GITHUB`, `LOCAL`
- Environment variable validation and Git repository detection
- AI provider and model configuration with intelligent defaults
- **Configuration Priority**: CLI args → Env vars → YAML file → Field defaults
- **Modify when:** Adding new configuration options, platforms, or validation logic

## 🛠️ Technology Stack

### Core Dependencies

```python
# CLI and HTTP
click>=8.1.0           # Modern CLI framework
httpx>=0.28.1          # HTTP client (sync & async, with streaming)
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

## 🚀 Complete Diff Fetching System

### Overview

The project implements an advanced diff fetching system for GitLab and GitHub that ensures **all files are included** in code reviews, even large files that platform APIs might omit.

### The Problem

Platform APIs (GitLab and GitHub) have limitations:
- **File omission**: Large files (>1MB typically) are excluded from API responses
- **No control**: Users don't know which files were omitted
- **Incomplete reviews**: AI might miss critical changes in large files

### The Solution

**Two-tier approach with automatic fallback:**

1. **Primary: HTTP `.diff` endpoint** (complete, always includes all files)
2. **Fallback: Standard API** (if HTTP method fails for any reason)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  _fetch_pull_request_diffs() / _fetch_merge_request_diffs()│
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─► Try HTTP .diff endpoint
                     │   │
                     │   ├─► Build URL (platform-specific)
                     │   │   - GitHub: https://github.com/owner/repo/pull/123.diff
                     │   │   - GitLab: https://gitlab.com/group/project/-/merge_requests/123.diff
                     │   │
                     │   ├─► Download with streaming (16KB chunks)
                     │   │   │
                     │   │   └─► FilteringStreamingDiffParser
                     │   │       │
                     │   │       ├─► Pre-filter binary files (by extension)
                     │   │       ├─► Pre-filter excluded patterns
                     │   │       ├─► Parse only relevant files
                     │   │       └─► Early stop at max_files limit
                     │   │
                     │   └─► Return parsed diffs ✓
                     │
                     └─► On failure: Automatic fallback to API
                         └─► Return API diffs (may be incomplete)
```

### Key Components

#### 1. FilteringStreamingDiffParser

**Location**: `src/ai_code_review/utils/diff_parser.py`

**Purpose**: Parse unified diff format incrementally with intelligent pre-filtering.

**Features**:
- **Streaming**: Processes diffs in chunks without loading entire file into memory
- **Pre-filtering**: Skips unwanted files BEFORE parsing their content
- **Binary detection**: Identifies binary files by extension
- **Statistics**: Tracks what was filtered and why

**Example Usage**:
```python
parser = FilteringStreamingDiffParser(
    should_exclude=lambda path: path.endswith('.lock')
)

async for chunk in response.content.iter_chunked(16384):
    for diff in parser.parse_chunk(chunk):
        # Process each relevant diff as it's parsed
        diffs.append(diff)

# Get final diffs from buffer
for diff in parser.finalize():
    diffs.append(diff)

# Check statistics
stats = parser.get_statistics()
# {'total_files': 100, 'filtered_files': 30, 'binary_files': 10, ...}
```

#### 2. Platform Client Implementation

**GitHub Client** (`src/ai_code_review/core/github_client.py`):

```python
async def _fetch_pull_request_diffs(
    self, pull_request: PullRequest.PullRequest
) -> list[PullRequestDiff]:
    """Fetch PR diffs with automatic fallback."""
    
    # 1. Try HTTP .diff method first
    diff_url = self._build_diff_url(
        pull_request.base.repo.full_name,
        pull_request.number
    )
    
    diffs = await self._fetch_and_parse_diff_with_prefiltering(
        diff_url,
        self._build_auth_headers()
    )
    
    if diffs:
        return self._apply_content_limits(diffs)
    
    # 2. Automatic fallback to API
    logger.info("Falling back to GitHub API for diffs")
    return await self._fetch_pull_request_diffs_via_api(pull_request)
```

**GitLab Client** (`src/ai_code_review/core/gitlab_client.py`):

Similar implementation with platform-specific URL building and SSL handling.

#### 3. URL Building (Platform-Specific)

**GitHub**:
```python
def _build_diff_url(self, project_id: str, pr_number: int) -> str:
    base_url = self.config.github_url
    
    if base_url == "https://github.com" or base_url == "https://api.github.com":
        # GitHub.com: use public URL
        return f"https://github.com/{project_id}/pull/{pr_number}.diff"
    else:
        # GitHub Enterprise: extract base from API URL
        api_base = base_url.replace("/api/v3", "").replace("/api", "")
        return f"{api_base}/{project_id}/pull/{pr_number}.diff"
```

**GitLab**:
```python
def _build_diff_url(
    self, 
    project_id: str, 
    mr_number: int,
    use_api_path: bool = False
) -> str:
    if use_api_path:
        # API-style path with project ID
        encoded_id = urllib.parse.quote(project_id, safe="")
        return f"{base_url}/projects/{encoded_id}/merge_requests/{mr_number}.diff"
    else:
        # Web-style path (preferred)
        return f"{base_url}/{project_id}/-/merge_requests/{mr_number}.diff"
```

### Performance Optimizations

#### 1. Pre-filtering (Before Parsing)

**Binary Files**:
```python
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf',
    '.zip', '.tar', '.gz', '.whl', '.pyc', '.so',
    # ... 50+ extensions
}

def is_binary_file(path: str) -> bool:
    return Path(path).suffix.lower() in BINARY_EXTENSIONS
```

**Excluded Patterns**:
```python
def should_exclude(path: str) -> bool:
    # Check against user's exclude_patterns
    for pattern in self.config.exclude_patterns:
        if PurePath(path).match(pattern):
            return True
    return False
```

#### 2. Early Stopping

```python
# Stop downloading/parsing when max_files is reached
if len(diffs) >= self.config.max_files:
    logger.info("Reached max_files limit during streaming")
    break
```

#### 3. Streaming Download

```python
# Download in 16KB chunks (balance between memory and speed)
async for chunk in response.content.iter_chunked(16384):
    # Process chunk immediately, don't accumulate in memory
    for diff in parser.parse_chunk(chunk):
        yield diff
```

### Statistics and Monitoring

The system logs detailed statistics after processing:

```python
{
    'total_files': 100,          # Total files encountered
    'filtered_files': 30,        # Files excluded by patterns
    'binary_files': 10,          # Binary files detected
    'included_files': 60,        # Files actually parsed
    'bytes_skipped': 47_185_920, # ~45MB not parsed
    'bytes_processed': 5_242_880, # ~5MB parsed
    'filter_ratio': 40.0,        # 40% filtered out
    'mb_skipped': 45.0,
    'mb_processed': 5.0,
}
```

### Error Handling

**Transparent Fallback**:
```python
try:
    # Try HTTP .diff method
    diffs = await fetch_via_http()
    if diffs:
        return diffs
except Exception as e:
    logger.warning(f"HTTP diff fetch failed: {e}")

# Always fall back to API (never fail)
return await fetch_via_api()
```

**Timeout Handling**:
```python
timeout = httpx.Timeout(self.config.diff_download_timeout)
async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
    async with client.stream("GET", url, headers=headers) as response:
        # ... process response
```

### Configuration

**User-facing configuration** (in `Config` model):
```python
diff_download_timeout: int = Field(
    default=120,
    description="Timeout for downloading complete diffs (seconds)"
)
```

**No user action needed** for the feature itself - it's automatic with transparent fallback.

### Testing Strategy

**Unit Tests**:
- `test_ai_code_review_diff_parser.py`: Parser logic
- `test_ai_code_review_github_client.py`: GitHub-specific HTTP fetching
- `test_ai_code_review_gitlab_client.py`: GitLab-specific HTTP fetching

**Test Coverage**:
- URL building for different platforms
- Successful HTTP fetch and parsing
- Non-200 HTTP responses (fallback)
- Pre-filtering (binary files, excluded patterns)
- Early stopping at max_files limit
- Statistics calculation
- Timeout handling

**Mock Pattern** (centralized in `conftest.py`):
```python
@contextmanager
def mock_httpx_client(diff_content: str, status: int = 200):
    """Fixture to mock httpx.AsyncClient for HTTP diff fetching tests."""
    
    # Create async iterator for aiter_bytes
    async def async_chunks():
        yield diff_content.encode("utf-8")
    
    mock_response = MagicMock()
    mock_response.status_code = status
    mock_response.aiter_bytes = MagicMock(return_value=async_chunks())
    # ... (See conftest.py for full implementation)
    
    with patch("httpx.AsyncClient") as mock_client_class:
        yield mock_client_class
```

### Extending the System

#### Adding a New Platform

1. Implement `_build_diff_url()` method
2. Implement `_build_auth_headers()` method
3. Implement `_fetch_and_parse_diff_with_prefiltering()` method
4. Implement fallback to platform API
5. Add platform-specific tests

**Example**: Adding Bitbucket support would require:
- Determining if Bitbucket has a `.diff` endpoint
- Implementing URL building for Bitbucket's URL structure
- Handling Bitbucket's authentication headers

#### Modifying Pre-filtering Logic

To add new file types to filter:

1. Update `BINARY_EXTENSIONS` in `diff_parser.py`
2. Or modify `should_exclude` logic in `BasePlatformClient`

#### Adjusting Performance Parameters

```python
# Chunk size for streaming download
CHUNK_SIZE = 16384  # 16KB (can be tuned)

# Minimum remaining space for truncation
MIN_REMAINING_CHARS = 20  # In _apply_content_limits()
```

### Future Improvements

**Potential Enhancements**:
- [ ] Compression support (Accept-Encoding: gzip)
- [ ] Parallel download of multiple MR/PR diffs
- [ ] Caching of diff downloads
- [ ] Progressive diff rendering for very large MRs
- [ ] Support for patch format (`.patch` endpoints)

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

#### Format Implementation Details

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

### 5. YAML Configuration Architecture

**Files:** `src/ai_code_review/models/config.py`, `src/ai_code_review/cli.py`

The YAML configuration system provides a **layered configuration approach** that prioritizes flexibility while maintaining security and usability.

#### Configuration Flow

**1. Configuration Loading Pipeline:**

```python
# CLI layer - merges all configuration sources
def _merge_layered_config(cli_args: dict[str, Any]) -> dict[str, Any]:
    # 1. Load YAML config file (if enabled and exists)
    config_file_data = Config._load_config_file_if_enabled(cli_args)

    # 2. Create base config from YAML + environment variables
    base_config = Config.from_layered_config(cli_args, config_file_data)

    # 3. Apply CLI argument overrides
    merged_data = Config._apply_cli_overrides(base_config, cli_args)

    return merged_data
```

**2. YAML File Detection Logic:**

```python
@classmethod
def _load_config_file_if_enabled(cls, cli_args: dict[str, Any]) -> dict[str, Any]:
    # Skip if explicitly disabled
    if cli_args.get("no_config_file"):
        return {}

    # Custom path via CLI argument
    if cli_args.get("config_file"):
        config_path = Path(cli_args["config_file"])
        is_explicit = True
    else:
        # Auto-detection: .ai_review/config.yml
        config_path = Path(".ai_review/config.yml")
        is_explicit = False

    # Load and validate YAML
    if config_path and config_path.exists():
        return yaml.safe_load(config_path.read_text())
```

**3. Configuration Priority System:**

```python
def from_layered_config(cls, cli_data: dict[str, Any], config_file_data: dict[str, Any]) -> Config:
    """
    Priority order:
    1. CLI arguments (cli_data) - highest priority
    2. Environment variables (from BaseSettings)
    3. YAML config file (config_file_data)
    4. Field defaults - lowest priority
    """
    # Environment variables loaded automatically by Pydantic BaseSettings
    # YAML config merged as additional source
    # CLI args applied as final overrides
```

#### YAML Implementation Details

**YAML Schema Validation:**

```python
# All config fields support YAML format conversion
class Config(BaseSettings):
    # List fields support both string and list formats
    exclude_patterns: list[str] = Field(
        default_factory=lambda: _DEFAULT_EXCLUDE_PATTERNS.copy()
    )

    # YAML: exclude_patterns: ["*.lock", "node_modules/**"]
    # ENV:  EXCLUDE_PATTERNS=*.lock,node_modules/**
    # CLI:  --exclude-files "*.lock" --exclude-files "node_modules/**"
```

**Error Handling and Validation:**

```python
# Comprehensive error handling for config files
try:
    data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML object")
except yaml.YAMLError as e:
    raise ValueError(f"Invalid YAML syntax: {e}")
except OSError as e:
    raise ValueError(f"Failed to read config file: {e}")
```

**Security Design:**

- **No Secrets in YAML**: API keys and tokens must use environment variables
- **Path Validation**: Validates config file paths for security
- **Schema Enforcement**: Pydantic validation prevents invalid configurations

#### Adding New Configuration Options

**Step 1: Add field to Config class:**

```python
class Config(BaseSettings):
    # New configuration option
    new_feature_enabled: bool = Field(
        default=True,
        description="Enable the new feature functionality"
    )

    # With validation if needed
    @field_validator("new_feature_enabled")
    @classmethod
    def validate_new_feature(cls, v: bool, info: ValidationInfo) -> bool:
        # Custom validation logic
        return v
```

**Step 2: Update CLI arguments:**

```python
@click.option(
    "--enable-new-feature/--disable-new-feature",
    default=None,
    help="Enable/disable new feature"
)
def main(..., enable_new_feature: bool | None = None):
    cli_args["new_feature_enabled"] = enable_new_feature
```

**Step 3: Update configuration example:**

```yaml
# .ai_review/config.yml.example
# New Feature Configuration
new_feature_enabled: true    # Enable new feature (default: true)
```

**Step 4: Add tests:**

```python
def test_new_feature_config_loading():
    """Test YAML config loading for new feature."""
    config_data = {"new_feature_enabled": False}
    config = Config.from_layered_config({}, config_data)
    assert config.new_feature_enabled == False
```

### 5. Modifying File Filtering

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
# Test local filtering
ai-code-review --local --exclude-files "*.test.*,docs/**"

# Test remote filtering
ai-code-review group/project 123 --exclude-files "*.test.*" --exclude-files "docs/**"

# Test with different file limits
ai-code-review --local --max-files 5 --max-file-context 1000
```

### 6. Adaptive Context Size Management

**Files:**
- `src/ai_code_review/providers/`
- `src/ai_code_review/core/review_engine.py`
- `src/ai_code_review/utils/constants.py`

The **Adaptive Context Size** system dynamically calculates optimal context window sizes for different AI providers based on the total content being processed.

#### Context Size Calculation Process

**1. Centralized Constants** (`utils/constants.py`):
```python
# Token estimation constants
SYSTEM_PROMPT_ESTIMATED_CHARS = 500
CHARS_TO_TOKENS_RATIO = 2.5

# Auto big-diffs threshold
AUTO_BIG_DIFFS_THRESHOLD_CHARS = 60000

# Derived constants
SYSTEM_PROMPT_ESTIMATED_TOKENS = int(SYSTEM_PROMPT_ESTIMATED_CHARS / CHARS_TO_TOKENS_RATIO)  # 200
```

**2. Total Content Calculation** (`review_engine.py`):
```python
# Calculate total content size including all components
project_context = self._get_project_context(pr_data)
project_context_chars = len(project_context) if project_context else 0
system_prompt_chars = SYSTEM_PROMPT_ESTIMATED_CHARS

total_content_chars = diff_size_chars + project_context_chars + system_prompt_chars

# Use total content for context window calculation
context_window_size = self.ai_provider.get_adaptive_context_size(
    diff_size_chars, project_context_chars, system_prompt_chars
)
```

**3. Provider-Specific Logic** (all providers):
```python
def get_adaptive_context_size(
    self,
    diff_size_chars: int,
    project_context_chars: int = 0,
    system_prompt_chars: int = SYSTEM_PROMPT_ESTIMATED_CHARS,
) -> int:
    # Calculate total content size
    total_content_chars = diff_size_chars + project_context_chars + system_prompt_chars

    # Provider-specific thresholds based on total content
    if total_content_chars > large_threshold:
        return large_context_size
    # ... provider-specific logic
```

#### Provider Context Limits

| **Provider** | **Standard** | **Large** | **Max** | **Strategy** |
|--------------|-------------|-----------|---------|--------------|
| **Ollama**   | 16K | 24K | 24K | Conservative (local compute) |
| **Anthropic** | 64K | 150K | 200K | Generous (cloud, high quality) |
| **Gemini**   | 64K | 256K | 512K | Very generous (massive context) |

#### Key Benefits

- **Precise Calculation**: Considers all content (diff + context + prompts)
- **No Magic Numbers**: Centralized constants prevent desynchronization
- **Auto Big-Diffs**: Automatically enables larger contexts when content > 60K chars
- **Better Resource Usage**: Optimal context allocation per provider
- **Comprehensive Logging**: Token distribution breakdown for debugging

#### Modifying Context Behavior

**Change estimation constants:**
```python
# utils/constants.py
SYSTEM_PROMPT_ESTIMATED_CHARS = 750        # Increase if prompts grow
CHARS_TO_TOKENS_RATIO = 3.0                # Adjust based on provider analysis
AUTO_BIG_DIFFS_THRESHOLD_CHARS = 80000     # Raise threshold for auto big-diffs
```

**Add new provider thresholds:**
```python
# providers/new_provider.py
def get_adaptive_context_size(self, diff_size_chars: int, ...) -> int:
    total_content_chars = diff_size_chars + project_context_chars + system_prompt_chars

    if total_content_chars > 100_000:
        return 128_000  # Custom large threshold
    else:
        return 32_000   # Custom standard
```

**Debug context calculations:**
```bash
LOG_LEVEL=DEBUG ai-code-review project/123
# Shows: diff_chars=50000, project_context_chars=15000, total_estimated_tokens=26000
# Also shows: auto_big_diffs_activated=true (when total > 60K chars)
```

### 7. Project Context Integration

**Files:** `src/ai_code_review/core/review_engine.py`, `src/ai_code_review/models/config.py`, `src/ai_code_review/cli.py`

The **Project Context** feature allows AI reviews to understand project-specific patterns, architecture, and "gotchas".

#### Project Context Integration Process

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

### 8. Extending Skip Review Mechanism

The **Skip Review mechanism** is designed to be extensible for organization-specific automation patterns.

#### Architecture Overview

```python
# Core implementation in review_engine.py
def should_skip_review(self, pr_data: PullRequestData) -> tuple[bool, str | None, str | None]:
    """
    Returns: (should_skip, reason, trigger)
    - should_skip: Boolean indicating if review should be skipped
    - reason: Category of skip (keyword, pattern, bot_author, etc.)
    - trigger: Specific trigger that caused the skip
    """
```

#### Skip Detection Logic Flow

```python
# Priority order (first match wins):
1. Keywords in title/description → "keyword"
2. Regex patterns in title → "pattern"
3. Documentation patterns (if enabled) → "documentation_pattern"
4. Bot authors → "bot_author"
5. Documentation-only files → "documentation_only"
```

#### Adding Custom Skip Criteria

**1. Custom Keywords** (`models/config.py`):

```python
# Extend SkipReviewConfig with organization-specific keywords
class SkipReviewConfig(BaseModel):
    keywords: list[str] = [
        "[skip review]", "[no review]", "[automated]", "[bot]",
        # Add organization-specific keywords
        "[hotfix]", "[emergency]", "[security-patch]",
        "[saltar revisión]",  # International support
    ]
```

**2. Custom Regex Patterns** (`models/config.py`):

```python
class SkipReviewConfig(BaseModel):
    patterns: list[str] = [
        # Built-in patterns...
        "^(chore|build|ci|feat|fix)\\(deps?\\):",

        # Add organization patterns
        "^\\[JIRA-\\d+\\] automated",     # JIRA tickets
        "^hotfix/automated-",              # Automated hotfixes
        "^security-patch:",                # Security patches
        "^i18n\\(.*\\):",                 # Internationalization
    ]
```

**3. Custom Bot Detection** (`models/config.py`):

```python
class SkipReviewConfig(BaseModel):
    bot_authors: list[str] = [
        # Built-in bots...
        "dependabot[bot]", "renovate[bot]",

        # Add organization bots
        "company-deploy-bot",
        "security-scanner[bot]",
        "translation-bot",
        "ci-automation@company.com",
    ]
```

**4. Advanced Custom Detection** (`core/review_engine.py`):

Add custom detection logic in the `should_skip_review` method:

```python
def should_skip_review(self, pr_data: PullRequestData) -> tuple[bool, str | None, str | None]:
    """Enhanced skip detection with custom logic."""

    # ... existing detection logic ...

    # CUSTOM: Skip if MR has specific labels (GitLab only)
    if hasattr(pr_data.info, 'labels') and pr_data.info.labels:
        skip_labels = {'automated', 'bot', 'dependencies', 'security-patch'}
        if any(label in skip_labels for label in pr_data.info.labels):
            return True, "label", f"label:{','.join(pr_data.info.labels)}"

    # CUSTOM: Skip if commit count is very high (likely generated)
    if pr_data.commit_count > 50:
        return True, "high_commit_count", f"commits:{pr_data.commit_count}"

    # CUSTOM: Skip if all files are in specific directories
    generated_dirs = {'generated/', 'dist/', 'build/', '.next/'}
    if pr_data.diffs and all(
        any(diff.file_path.startswith(gen_dir) for gen_dir in generated_dirs)
        for diff in pr_data.diffs
    ):
        return True, "generated_files", "generated_directories"

    # CUSTOM: Skip based on file size (very large auto-generated files)
    large_files = [
        diff for diff in pr_data.diffs
        if len(diff.diff) > 10000  # Very large diffs
    ]
    if len(large_files) > 5:  # Many large files
        return True, "large_files", f"large_files:{len(large_files)}"

    return False, None, None
```

#### Configuration Integration

**1. Add to Default Configuration** (`models/config.py`):

```python
@field_validator("patterns", "documentation_patterns")
@classmethod
def validate_patterns(cls, patterns: list[str]) -> list[str]:
    """Validate that all patterns compile as valid regex."""
    validated_patterns = []
    for pattern in patterns:
        try:
            re.compile(pattern)
            validated_patterns.append(pattern)
        except re.error as e:
            # Organization-specific: log warnings but continue
            logger.warning(f"Invalid skip pattern: {pattern} - {e}")
    return validated_patterns
```

**2. Environment Variable Support** (`models/config.py`):

```python
# Add new environment variables
class Config(BaseSettings):
    # ... existing fields ...

    # Custom skip configuration
    skip_on_high_commit_count: bool = False
    skip_commit_threshold: int = 50
    skip_generated_directories: bool = True

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        # Map custom environment variables
        extra="ignore",
    )
```

#### Testing Custom Skip Logic

**1. Unit Tests** (`tests/unit/test_skip_review.py`):

```python
class TestCustomSkipLogic:
    """Test custom skip detection logic."""

    def test_skip_high_commit_count(self) -> None:
        """Test skipping PRs with very high commit count."""
        # Create PR data with many commits
        pr_data = create_pr_data_with_commits(commit_count=75)

        config = Config(skip_review=SkipReviewConfig(enabled=True))
        engine = ReviewEngine(config)

        should_skip, reason, trigger = engine.should_skip_review(pr_data)

        assert should_skip is True
        assert reason == "high_commit_count"
        assert trigger == "commits:75"

    def test_skip_generated_directories(self) -> None:
        """Test skipping PRs with only generated files."""
        pr_data = create_pr_data_with_files([
            "generated/api.ts",
            "dist/bundle.js",
            "build/output.css"
        ])

        # ... test implementation
```

**2. Integration Tests**:

```bash
# Test custom skip logic with real data
ai-code-review --test-skip-only project/123 --dry-run

# Test with custom config
ai-code-review --config-file custom-skip-config.yml --test-skip-only project/123
```

#### Adding New Skip Reasons

**1. Extend Exit Handling** (`cli.py`):

```python
# Handle new skip reasons with specific messaging
except ReviewSkippedError as e:
    if "high_commit_count" in str(e):
        click.echo("⚡ Skipped: Too many commits (likely auto-generated)", err=True)
    elif "generated_files" in str(e):
        click.echo("⚡ Skipped: Only generated/build files changed", err=True)
    else:
        click.echo(f"⚡ Skipped: {e}", err=True)

    sys.exit(EXIT_CODE_SKIPPED)
```

**2. Enhanced Logging** (`core/review_engine.py`):

```python
# Add structured logging for skip reasons
logger.info(
    "Review skipped",
    reason=skip_reason,
    trigger=skip_trigger,
    pr_id=pr_data.info.id,
    author=pr_data.info.author,
    file_count=pr_data.file_count,
    commit_count=pr_data.commit_count,
)
```

#### Key Extension Points

- **Detection Logic**: `should_skip_review()` method
- **Configuration**: `SkipReviewConfig` model
- **Patterns**: YAML configuration files
- **Testing**: Comprehensive test coverage in `test_skip_review.py`
- **CLI Integration**: `--test-skip-only` for debugging
- **Logging**: Structured logs for monitoring and analytics

#### Best Practices

1. **Gradual Rollout**: Test new skip logic with `--test-skip-only` first
2. **Monitoring**: Log skip decisions for analysis and tuning
3. **Fallback**: Always allow manual override with `--no-skip-detection`
4. **Documentation**: Update team docs when adding custom patterns
5. **Testing**: Write unit tests for all custom skip logic

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
