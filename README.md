# AI Code Review

AI-powered code review tool with **3 powerful use cases**:

- 🤖 **CI Integration** - Automated reviews in your CI/CD pipeline (GitLab or GitHub)
- 🔍 **Local Reviews** - Review your local changes before committing
- 🌐 **Remote Reviews** - Analyze existing MRs/PRs from the terminal

## 📑 Table of Contents

- [🚀 Primary Use Case: CI/CD Integration](#-primary-use-case-cicd-integration)
- [⚙️ Secondary Use Cases](#️-secondary-use-cases)
  - [Local Usage (Container)](#local-usage-container)
  - [Local Usage (CLI Tool)](#local-usage-cli-tool)
  - [Remote Reviews](#remote-reviews)
- [🔧 Configuration](#-configuration)
- [⚡ Smart Skip Review](#-smart-skip-review)
- [For Developers](#for-developers)
- [🔧 Common Issues](#-common-issues)
- [📖 Documentation](#-documentation)
- [🤖 AI Tools Disclaimer](#-ai-tools-disclaimer)
- [📄 License](#-license)
- [👥 Author](#-author)

## 🚀 Primary Use Case: CI/CD Integration

This is the primary and recommended way to use the AI Code Review tool.

### GitLab CI

Add to `.gitlab-ci.yml`:
```yaml
ai-review:
  stage: code-review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY  # Set in CI/CD variables
  script:
    - ai-code-review --post
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
  allow_failure: true
```

### GitHub Actions

Add to `.github/workflows/ai-review.yml`:
```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    container:
      image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
    steps:
      - name: Run AI Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          AI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: ai-code-review --pr-number ${{ github.event.pull_request.number }} --post
```

## ⚙️ Secondary Use Cases

### Local Usage (Container)

This is the recommended way to use the tool locally, as it doesn't require any installation on your system.

```bash
# Review local changes
podman run -it --rm -v .:/app -w /app \
       registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest \
       ai-code-review --local

# Review a remote MR
podman run -it --rm -e GITLAB_TOKEN=$GITLAB_TOKEN -e AI_API_KEY=$AI_API_KEY \
       registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest \
       ai-code-review group/project 123
```

> **Note**: You can use `docker` instead of `podman` and the command should work the same.

### Local Usage (CLI Tool)

This is a good option if you have Python installed and want to use the tool as a CLI command.

> **Note on package vs. command name:** The package is registered on PyPI as `ai-code-review-cli`, but for ease of use, the command to execute remains `ai-code-review`.

`pipx` is a more mature and well-known tool for the same purpose. It handles the package vs. command name difference automatically.

```bash
# Install pipx
pip install pipx
pipx ensurepath

# Install the package
pipx install ai-code-review-cli

# Run the command
ai-code-review --local
```

### Remote Reviews

You can also analyze existing MRs/PRs from your terminal.

```bash
# GitLab MR
ai-code-review group/project 123

# GitHub PR
ai-code-review --platform github owner/repo 456

# Save to file
ai-code-review group/project 123 -o review.md

# Post the review to the MR/PR
ai-code-review group/project 123 --post
```

## 🔧 Configuration

### Required Setup

#### 1. Platform Token (Not needed for local reviews)

```bash
# For GitLab remote reviews
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx

# For GitHub remote reviews
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Local reviews don't need platform tokens! 🎉
```

#### 2. AI API Key

```bash
# Get key from: https://makersuite.google.com/app/apikey
export AI_API_KEY=your_gemini_api_key_here
```

### Configuration Methods (Priority Order)

The tool supports **4 configuration methods** with the following priority:

1. **🔴 CLI Arguments** (highest priority) - `--provider anthropic --model claude-sonnet-4-20250514`
2. **🟡 Environment Variables** - `export AI_PROVIDER=anthropic`
3. **🟢 Configuration File** - `.ai_review/config.yml`
4. **⚪ Field Defaults** (lowest priority) - Built-in defaults

### Configuration File

Create a YAML configuration file for persistent settings:

```bash
# Create from template
cp .ai_review/config.yml.example .ai_review/config.yml

# Edit your project settings
nano .ai_review/config.yml
```

**Key benefits:**
- ✅ **Project-specific settings** - Different configs per repository
- ✅ **Team sharing** - Commit to git for consistent team settings
- ✅ **Reduced typing** - Set common options once
- ✅ **Layered override** - CLI arguments still override everything

**File locations:**
- **Auto-detected**: `.ai_review/config.yml` (loaded automatically if exists)
- **Custom path**: `--config-file path/to/custom.yml`
- **Disable loading**: `--no-config-file` flag

### Environment Variables

For sensitive data and CI/CD environments:
```bash
# Copy template
cp env.example .env

# Edit and set your tokens
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
AI_API_KEY=your_gemini_api_key_here
```

### Common Options

```bash
# Different AI providers
ai-code-review project/123 --provider anthropic  # Claude
ai-code-review project/123 --provider ollama     # Local Ollama

# Custom server URLs
ai-code-review project/123 --gitlab-url https://gitlab.company.com

# Output options
ai-code-review project/123 -o review.md          # Save to file
ai-code-review project/123 2>logs.txt            # Logs to stderr
```

**For all configuration options, troubleshooting, and advanced usage → see [User Guide](docs/user-guide.md)**

### Team/Organization Context

For teams working on multiple projects, you can specify a **shared team context** that applies organization-wide:

```bash
# Remote team context (recommended - stored in central repo)
export TEAM_CONTEXT_FILE=https://gitlab.com/org/standards/-/raw/main/review.md
ai-code-review --local

# Or use CLI option
ai-code-review project/123 --team-context https://company.com/standards/review.md --post

# Local team context file
ai-code-review --team-context ../team-standards.md --local
```

**Use cases:**
- Organization-wide coding standards
- Security requirements and compliance rules
- Team conventions shared across projects
- Industry-specific guidelines (HIPAA, GDPR, etc.)

**Priority order:** Team context → Project context → Commit history

This allows maintaining org standards while individual projects add specific guidelines.

**See [User Guide - Team Context](docs/user-guide.md#-teamorganization-context) for complete documentation.**

### Intelligent Review Context (Two-Phase Synthesis)

The tool uses a **two-phase approach** to incorporate previous reviews and avoid repeating mistakes:

**Phase 1 - Synthesis (automatic):**
- Fetches **ALL** comments and reviews (including resolved ones)
- Uses a fast model (e.g., `gemini-2.5-flash`) to synthesize key insights
- Identifies author corrections to previous AI reviews
- Generates concise summary (<500 words)

**Phase 2 - Main Review:**
- Uses synthesis as context to avoid repeating mistakes
- Focuses on code changes with awareness of discussions

**Benefits:**
- ✅ Prevents repeating invalidated suggestions
- ✅ Reduces token usage (synthesis is much shorter than raw comments)
- ✅ Lower costs (fast model for preprocessing)
- ✅ Better quality (focused insights vs raw data)

**Configuration:**
```yaml
# Enable/disable (default: enabled)
enable_review_context: true
enable_review_synthesis: true

# Custom synthesis model (optional)
synthesis_model: "gemini-2.5-flash"  # Default for Gemini
# synthesis_model: "claude-3-5-haiku-20241022"  # For Anthropic
# synthesis_model: "gpt-4o-mini"  # For OpenAI
```

**Skips automatically when:**
- No comments/reviews exist (first review)
- Feature is disabled

## ⚡ Smart Skip Review

**AI Code Review automatically skips unnecessary reviews** to reduce noise and costs:

- 🔄 **Dependency updates** (`chore(deps): bump lodash 4.1.0 to 4.2.0`)
- 🤖 **Bot changes** (from `dependabot[bot]`, `renovate[bot]`)
- 📝 **Documentation-only** changes (if enabled)
- 🏷️ **Tagged PRs/MRs** (`[skip review]`, `[automated]`)
- 📝 **Draft/WIP PRs/MRs** (work in progress)

**Result:** Focus on meaningful changes, save API costs, faster CI/CD pipelines.

> **📖 Learn more:** Configuration, customization, and CI integration → [User Guide - Skip Review](docs/user-guide.md#smart-skip-review)

## For Developers

### Development Setup

```bash
# Install using uv (recommended)
uv sync

# Or with pip
pip install -e .
```

> To install or learn more about `uv`, check here:
[uv](https://docs.astral.sh/uv)

## 🔧 Common Issues

### gRPC Warnings with Google Gemini

When using Google Gemini provider, you may see harmless gRPC connection warnings:

```
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1759934851.372144 Other threads are currently calling into gRPC, skipping fork() handlers
```

**These warnings are harmless and don't affect functionality.** To suppress them:

```bash
# Suppress warnings by redirecting stderr
ai-code-review --local 2>/dev/null
ai-generate-context . 2>/dev/null

# Or use alternative provider (no warnings)
ai-code-review --local --provider ollama
```

## 📖 Documentation

- **[User Guide](docs/user-guide.md)** - Complete usage, configuration, and troubleshooting
- **[Context Generator Guide](docs/context-generator.md)** - AI context generation for better reviews (requires Git repository)
- **[Context7 Integration Guide](docs/context7-integration.md)** - Enhanced reviews with official library documentation (optional)
- **[Developer Guide](docs/developer-guide.md)** - Development setup, architecture, and contributing

## 🤖 AI Tools Disclaimer

<details>
<summary>This project was developed with the assistance of artificial intelligence tools</summary>

**Tools used:**
- **Cursor**: Code editor with AI capabilities
- **Claude-Sonnet-4**: Anthropic's language model (claude-sonnet-4-20250514)

**Division of responsibilities:**

**AI (Cursor + Claude-Sonnet-4)**:
- 🔧 Initial code prototyping
- 📝 Generation of examples and test cases
- 🐛 Assistance in debugging and error resolution
- 📚 Documentation and comments writing
- 💡 Technical implementation suggestions

**Human (Juanje Ojeda)**:
- 🎯 Specification of objectives and requirements
- 🔍 Critical review of code and documentation
- 💬 Iterative feedback and solution refinement
- ✅ Final validation of concepts and approaches

**Collaboration philosophy**: AI tools served as a highly capable technical assistant, while all design decisions, educational objectives, and project directions were defined and validated by the human.
</details>

## 📄 License

MIT License - see LICENSE file for details.

## 👥 Author

- **Author:** Juanje Ojeda
- **Email:** juanje@redhat.com
- **URL:** <https://gitlab.com/redhat/edge/ci-cd/ai-code-review>
