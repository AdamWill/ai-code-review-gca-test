# AI Code Review Tool

AI-powered Python CLI tool that provides automated code review assistance for
**GitLab Merge Requests** and **GitHub Pull Requests**. The tool analyzes diffs using AI models and generates
structured feedback to support human reviewers across both platforms.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- **Platform Access Token** (REQUIRED):
  - **GitLab**: Personal Access Token with `api`, `read_user`, `read_repository` scopes
  - **GitHub**: For GitHub Actions use automatic `GITHUB_TOKEN` (with proper permissions), for local use create Personal Access Token with `repo` scope
- **For Production/CI**: AI API key from supported providers:
  - Google Gemini API key (default provider)
  - Anthropic Claude API key (recommended alternative)
  - OpenAI API key (supported)
- **For Local Development**: Ollama server running locally (optional)

### Installation

```bash
# Install using uv
uv sync --dev

# Or with pip
pip install -e .
```

### Quick Setup

⚠️ **IMPORTANT: You MUST configure platform access tokens before using the tool:**

```bash
# For GitLab (set GitLab token)
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx

# For GitHub (set GitHub token)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Or create a .env file (recommended)
cp env.example .env
# Then edit .env and set your platform tokens
```

### Usage

#### GitLab Merge Requests

```bash
# Review a GitLab MR (uses Gemini by default)
AI_API_KEY=your_gemini_key ai-code-review --platform gitlab --project-id "group/project" --mr-iid 123

# Post review as MR comment (typical CI/CD usage)
AI_API_KEY=your_gemini_key ai-code-review --platform gitlab --project-id "group/project" --mr-iid 123 --post
```

#### GitHub Pull Requests

```bash
# Review a GitHub PR
AI_API_KEY=your_gemini_key ai-code-review --platform github --project-id "owner/repo" --pr-number 123

# Post review as PR comment
AI_API_KEY=your_gemini_key ai-code-review --platform github --project-id "owner/repo" --pr-number 123 --post

```

#### Advanced Options

```bash
# Use Anthropic Claude for high-quality reviews (GitLab)
AI_API_KEY=your_claude_key ai-code-review --platform gitlab --project-id "group/project" --mr-iid 123 --provider anthropic

# Use Anthropic Claude for GitHub
AI_API_KEY=your_claude_key ai-code-review --platform github --project-id "owner/repo" --pr-number 123 --provider anthropic

# Use Ollama for local development (no API key needed) - GitLab
ai-code-review --platform gitlab --project-id "group/project" --mr-iid 123 --provider ollama

# Use Ollama for GitHub
ai-code-review --platform github --project-id "owner/repo" --pr-number 123 --provider ollama

# For large diffs (forces 24K context window)
ai-code-review --platform gitlab --project-id "group/project" --mr-iid 123 --big-diffs

# Dry run mode (no API calls, useful for testing)
ai-code-review --platform github --project-id "owner/repo" --pr-number 123 --dry-run
```

### CI/CD Integration

#### GitLab CI/CD Usage

```yaml
# .gitlab-ci.yml
ai-review:
  stage: test
  image: registry.gitlab.com/juanjeojeda/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY  # Set as masked/protected variable
    # Alternative: AI_API_KEY: $ANTHROPIC_API_KEY  # For Claude
  script:
    - ai-code-review --platform gitlab --post
  allow_failure: true  # Do not block the pipeline if the API fails
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

#### GitHub Actions Usage

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    container:
      image: registry.gitlab.com/juanjeojeda/ai-code-review:latest
    steps:
      - name: Run AI Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          AI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          ai-code-review --platform github --pr-number ${{ github.event.pull_request.number }} --post
```

## 🔧 Configuration

The tool supports comprehensive configuration through environment variables.

### ⚠️ REQUIRED Configuration

**You MUST set platform access tokens before using the tool:**

#### GitLab Setup

```bash
# GitLab Personal Access Token
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
```

#### GitHub Setup

```bash
# GitHub Personal Access Token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

#### Environment File (RECOMMENDED)

```bash
# Create and configure .env file
cp env.example .env
# Edit .env and set your platform tokens
```

**How to get tokens:**

**GitLab Token:**
1. Go to GitLab → Settings → Access Tokens
2. Create a token with scopes: `api`, `read_user`, `read_repository`

**GitHub Token:**
1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Create a token with scopes: `repo`, `read:org`
3. Copy the token and use it in your configuration

### 🤖 AI Provider API Keys

**For Anthropic Claude (recommended):**
1. Go to [Anthropic Console](https://console.anthropic.com/account/keys)
2. Create an API key
3. Set as `AI_API_KEY` environment variable

**For Google Gemini:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Set as `AI_API_KEY` environment variable

### 📝 All Configuration Options

Copy `env.example` to `.env` and customize as needed:

```bash
# Required - Platform Access Tokens
export GITLAB_TOKEN=glpat_xxxxxxxxxxxx         # For GitLab platform
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx           # For GitHub platform

# Platform Configuration
export PLATFORM_PROVIDER=gitlab                # gitlab or github (default: gitlab)
export GITLAB_URL=https://gitlab.com           # GitLab instance URL
export GITHUB_URL=https://api.github.com       # GitHub API URL (for Enterprise)

# AI Provider settings (with defaults)
export AI_PROVIDER=gemini                      # gemini, anthropic, openai, ollama
export AI_MODEL=gemini-2.5-pro                 # Provider-specific model name
export AI_API_KEY=your_gemini_api_key_here     # Required for cloud providers

# AI Model parameters (defaults optimized for code review)
export TEMPERATURE=0.1                         # 0.0-2.0, lower = more deterministic
export MAX_TOKENS=8000                         # Maximum response tokens
export HTTP_TIMEOUT=5.0                        # HTTP timeout in seconds

# Ollama configuration (for local development)
export OLLAMA_BASE_URL=http://localhost:11434

# Processing limits
export MAX_CHARS=100000                        # Max characters from diff
export MAX_FILES=100                           # Max files to process

# Optional features
export LANGUAGE_HINT=python                   # Programming language hint
export DRY_RUN=false                          # Enable dry-run mode (no API calls)
export BIG_DIFFS=false                        # Force large context (24K)
export LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Configuration Validation:**

- URLs are validated for proper format
- AI model names are validated for basic format requirements
- Log levels are validated against standard Python logging levels
- All invalid configurations will raise clear error messages at startup

## 🧠 Adaptive Context Windows

The tool automatically adapts context window sizes for optimal performance:

- **Standard MRs** (≤60K chars): 16K context window for efficiency
- **Large MRs** (>60K chars): Auto-activated 24K context window
- **Manual override**: `--big-diffs` forces 24K context regardless of size
- **CI/CD friendly**: Auto-detection works without human intervention

This eliminates information loss from diff truncation while maintaining
optimal memory usage.

## 🗂️ File Filtering

The tool automatically excludes common non-reviewable files from AI analysis
to reduce noise and token usage:

### Default Exclusions

By default, the following file patterns are excluded:

- **Lockfiles**: `*.lock`, `package-lock.json`, `yarn.lock`, etc.
- **Minified files**: `*.min.js`, `*.min.css`, `*.map`
- **Build outputs**: `dist/**`, `build/**`
- **Dependencies**: `node_modules/**`, `__pycache__/**`
- **Generated files**: `*.egg-info/**`

### Configuration Options

#### Environment Variable

```bash
# Comma-separated list of glob patterns
export EXCLUDE_PATTERNS="*.lock,*.min.js,node_modules/**,dist/**"

# Disable all filtering (include everything)
export EXCLUDE_PATTERNS=""
```

#### CLI Options

```bash
# Add additional exclusion patterns
ai-code-review --exclude-files "*.test.js" \
    --exclude-files "**/temp/**" group/project 123

# Disable all file filtering (include lockfiles, build artifacts, etc.)
ai-code-review --no-file-filtering group/project 123

# Example: Review only source code, exclude tests and docs
ai-code-review --exclude-files "**/*test*" \
    --exclude-files "docs/**" group/project 123
```

#### Pattern Format

- **Simple wildcards**: `*.js`, `*.lock`
- **Directory patterns**: `dist/**`, `node_modules/**`
- **Recursive matching**: `**/build/**` (matches nested build dirs)
- **Exact files**: `package-lock.json`

### Benefits

File filtering provides several advantages:

- **🚀 Faster reviews**: Skip irrelevant generated files
- **💰 Lower costs**: Reduce token usage significantly
- **🎯 Better focus**: AI reviews only meaningful code changes
- **⚡ Improved performance**: Less processing overhead

### Example Impact

For a typical JavaScript project MR:

```text
Without filtering: 45,000 chars (18K tokens) → $0.54 cost
With filtering:     8,500 chars (3.4K tokens) → $0.10 cost
Savings:           ~81% reduction in tokens and cost
```

## 🧪 Testing the New Gemini Integration

### Local Testing

#### 1. **Test with Gemini (Production Default)**

```bash
# Get your Gemini API key from: https://makersuite.google.com/app/apikey
export AI_API_KEY="your_gemini_api_key_here"
export GITLAB_TOKEN="your_gitlab_token"

# Test dry-run first (no API costs)
ai-code-review group/project 123 --dry-run

# Test real review generation
ai-code-review group/project 123

# Test posting to GitLab
ai-code-review group/project 123 --post
```

#### 2. **Test with Anthropic Claude**

```bash
# Test with Anthropic (requires API key)
AI_API_KEY=your_claude_key ai-code-review group/project 123 --provider anthropic --dry-run
AI_API_KEY=your_claude_key ai-code-review group/project 123 --provider anthropic

# Check Anthropic connectivity
AI_API_KEY=your_claude_key ai-code-review --provider anthropic --health-check
```

#### 3. **Test with Ollama (Local Development)**

```bash
# Start Ollama server first
ollama serve

# Pull recommended model
ollama pull qwen2.5-coder:7b

# Test with Ollama (no API key needed)
ai-code-review group/project 123 --provider ollama --dry-run
ai-code-review group/project 123 --provider ollama
```

#### 4. **Health Check**

```bash
# Check Gemini connectivity
AI_API_KEY="your_key" ai-code-review --health-check

# Check Ollama connectivity
ai-code-review --provider ollama --health-check
```

### GitLab CI/CD Testing

#### 1. **Setup CI/CD Variables**

In your GitLab project, go to **Settings → CI/CD → Variables** and add:

```bash
# Required - Add as Protected + Masked variable
GEMINI_API_KEY = your_google_gemini_api_key_here

# Optional - Override defaults if needed
AI_PROVIDER = gemini
AI_MODEL = gemini-2.5-pro
```

#### 2. **Add CI Job to `.gitlab-ci.yml`**

```yaml
stages:
  - test
  - review

# Your existing tests...

ai-code-review:
  stage: review
  image: $CI_REGISTRY_IMAGE:latest  # Uses your built container
  script:
    - ai-code-review --post --health-check
  variables:
    AI_API_KEY: $GEMINI_API_KEY
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
  allow_failure: true  # Don't block MRs on review failures
```

#### 3. **Test the Pipeline**

1. **Create a test MR** in your project
2. **Push changes** to trigger the pipeline
3. **Check the job logs** for successful API connection
4. **Verify the review** appears as MR comment

### Expected Output

#### Successful Gemini Review

```
🚀 Starting AI code review...
  Project: group/project
  MR IID: 123
  Provider: gemini
  Model: gemini-2.5-pro

📥 Fetching MR data from GitLab...
🧠 Generating AI review with gemini...
📝 Review generated successfully!
✅ Review posted to GitLab MR
```

#### Health Check Success

```json
{
  "status": "healthy",
  "provider": "gemini",
  "model": "gemini-2.5-pro",
  "api_key_configured": true
}
```

## 🧪 Development

### Setup

```bash
# Install dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run manual checks
uv run ruff check . --fix
uv run ruff format .
uv run mypy src/
uv run pytest
```

### Pre-commit

This project uses pre-commit to automatically validate code before commits.

#### Setup Pre-commit

```bash
# Install hooks (one time only)
uv run pre-commit install
```

#### Running Pre-commit

```bash
# Run all checks manually
uv run pre-commit run --all-files

# Run on modified files only
uv run pre-commit run
```

#### Common errors

```bash
# Auto-fix linting/formatting
uv run ruff check . --fix && uv run ruff format .

# Check types
uv run mypy src/

# Skip hooks (exceptional cases only)
git commit --no-verify -m "message"
```

### Testing

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html
```

## 📚 Documentation

This is an MVP implementation focusing on:
- Basic GitLab MR diff fetching
- Production AI processing with Google Gemini (default)
- Local development with Ollama (optional)
- Structured review generation
- Simple CLI interface
- Ready for GitLab CI/CD integration

## 🤖 AI Tools Disclaimer

This project was developed with the assistance of artificial intelligence tools:

**Tools used:**
- **Cursor**: Code editor with AI capabilities
- **Claude-4-Sonnet**: Anthropic's language model

**Division of responsibilities:**

**AI (Cursor + Claude-4-Sonnet)**:
- 🔧 Initial code prototyping
- 📝 Generation of examples and test cases
- 🐛 Assistance in debugging and error resolution
- 📚 Documentation and comments writing
- 💡 Technical implementation suggestions

**Human (Juanje Ojeda)**:
- 🎯 Specification of objectives and requirements
- 🔍 Critical review of code and documentation
- 💬 Iterative feedback and solution refinement
- 📋 Definition of project's educational structure
- ✅ Final validation of concepts and approaches

**Collaboration philosophy**: AI tools served as a highly capable technical
assistant, while all design decisions, educational objectives, and project
directions were defined and validated by the human.

## 📄 License

MIT License - see LICENSE file for details.

## 👥 Author

**Author:** Juanje Ojeda\
**Email:** juanje@redhat.com\
**URL:** <https://gitlab.com/juanjeojeda/ai-code-review>
