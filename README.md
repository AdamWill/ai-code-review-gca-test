# AI Code Review Tool

AI-powered Python CLI tool that provides automated code review assistance for GitLab Merge Requests. The tool analyzes MR diffs using AI models and generates structured feedback to support human reviewers.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Ollama server running locally (for development)
- GitLab Personal Access Token

### Installation

```bash
# Install using uv
uv sync --dev

# Or with pip
pip install -e .
```

### Usage

```bash
# Review a GitLab MR
ai-code-review --project-id "group/project" --mr-iid 123

# With Ollama (default for local development)
ai-code-review --project-id "group/project" --mr-iid 123 --provider ollama

# Post review as MR comment
ai-code-review --project-id "group/project" --mr-iid 123 --post

# For large MRs (forces 24K context window)
ai-code-review --project-id "group/project" --mr-iid 123 --big-diffs

# Dry run mode (no API calls, useful for testing)
ai-code-review --project-id "group/project" --mr-iid 123 --dry-run
```

## 🔧 Configuration

The tool supports comprehensive configuration through environment variables. Copy `env.example` to `.env` and customize as needed:

```bash
# Required
export GITLAB_TOKEN=glpat_xxxxxxxxxxxx         # GitLab Personal Access Token

# Core settings (with defaults)
export GITLAB_URL=https://gitlab.com           # GitLab instance URL
export AI_PROVIDER=ollama                      # ollama, openai, gemini, anthropic
export AI_MODEL=qwen2.5-coder:7b              # AI model name

# AI Model parameters (defaults optimized for code review)
export TEMPERATURE=0.1                         # 0.0-2.0, lower = more deterministic
export MAX_TOKENS=4096                         # Maximum response tokens
export HTTP_TIMEOUT=5.0                       # HTTP timeout in seconds

# Ollama configuration (for local development)
export OLLAMA_BASE_URL=http://localhost:11434

# Processing limits
export MAX_CHARS=100000                        # Max characters from diff
export MAX_FILES=100                          # Max files to process

# Optional features
export LANGUAGE_HINT=python                   # Programming language hint
export DRY_RUN=false                          # Enable dry-run mode (no API calls)
export BIG_DIFFS=false                        # Force large context (24K) - auto-activated for >60K chars
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

This eliminates information loss from diff truncation while maintaining optimal memory usage.

## 🧪 Development

### Setup
```bash
# Install dependencies
uv sync --dev

# Run pre-commit checks
uv run ruff check . --fix
uv run ruff format .
uv run mypy src/
uv run pytest
```

### Testing
```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html
```

## 📚 Documentation

This is an MVP (Phase 1) implementation focusing on:
- Basic GitLab MR diff fetching
- Local AI processing with Ollama
- Structured review generation
- Simple CLI interface

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

**Collaboration philosophy**: AI tools served as a highly capable technical assistant, while all design decisions, educational objectives, and project directions were defined and validated by the human.

## 📄 License

MIT License - see LICENSE file for details.

## 👥 Author

**Author:** Juanje Ojeda  
**Email:** juanje@redhat.com  
**URL:** https://gitlab.com/juanjeojeda/ai-code-review
