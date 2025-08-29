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
```

## 🔧 Configuration

Set your GitLab token:
```bash
export GITLAB_TOKEN=glpat_xxxxxxxxxxxx
```

For local development with Ollama:
```bash
export AI_PROVIDER=ollama
export AI_MODEL=qwen2.5-coder:7b
export OLLAMA_BASE_URL=http://localhost:11434
```

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
