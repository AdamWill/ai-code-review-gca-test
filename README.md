# AI Code Review

AI-powered code review tool with **3 powerful use cases**:

🔍 **Local Reviews** - Review your local changes before committing
🌐 **Remote Reviews** - Analyze existing MRs/PRs from the terminal
🤖 **CI Integration** - Automated reviews in your CI/CD pipeline

## 🚀 Quick Start

### Installation

```bash
# Install using uv (recommended)
uv sync

# Or with pip
pip install -e .
```

> To install or learn more about `uv`, check here:
[uv](https://docs.astral.sh/uv)

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

## 📋 Usage

### 🔍 Use Case 1: Local Code Review

**Review your local changes before committing:**

```bash
# Review current local changes vs main branch
ai-code-review --local

# Review against specific target branch
ai-code-review --local --target-branch develop

# Save review to file (terminal-friendly format)
ai-code-review --local -o local-review.md
```

### 🌐 Use Case 2: Remote Code Review

**Analyze existing MRs/PRs from terminal (no posting):**

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

### 🤖 Use Case 3: CI/CD Integration

#### GitLab CI

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

#### GitHub Actions

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

## 🔧 Configuration

### Basic Configuration

Create `.env` file for local development:
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

## 📖 Documentation

- **[User Guide](docs/user-guide.md)** - Complete usage, configuration, and troubleshooting
- **[Developer Guide](docs/developer-guide.md)** - Development setup, architecture, and contributing

## 🤖 AI Tools Disclaimer

<details>
<summary>This project was developed with the assistance of artificial intelligence tools</summary>

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
- ✅ Final validation of concepts and approaches

**Collaboration philosophy**: AI tools served as a highly capable technical assistant, while all design decisions, educational objectives, and project directions were defined and validated by the human.
</details>

## 📄 License

MIT License - see LICENSE file for details.

## 👥 Author

**Author:** Juanje Ojeda\
**Email:** juanje@redhat.com\
**URL:** <https://gitlab.com/redhat/edge/ci-cd/ai-code-review>
