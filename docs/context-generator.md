# AI Context Generator

The AI Context Generator is a powerful tool that automatically analyzes your project and creates comprehensive context files to improve AI-powered code reviews.

## Table of Contents

- [Overview](#overview)
- [Installation & Setup](#installation--setup)
  - [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Supported AI Providers](#supported-ai-providers)
- [Usage](#usage)
  - [Basic Usage](#basic-usage)
  - [Partial Updates](#partial-updates)
  - [Advanced Options](#advanced-options)
- [Generated Sections](#generated-sections)
  - [Automatic Sections](#automatic-sections)
  - [Manual Sections](#manual-sections)
- [Best Practices](#best-practices)
  - [Workflow Recommendations](#workflow-recommendations)
  - [What to Keep Manual](#what-to-keep-manual)
  - [What to Keep Automatic](#what-to-keep-automatic)
  - [Integration Patterns](#integration-patterns)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Debug Mode](#debug-mode)
- [Integration with AI Code Review](#integration-with-ai-code-review)
- [Examples](#examples)
- [Supported Project Types](#supported-project-types)

## Overview

The context generator analyzes your **Git-tracked files**, project structure, dependencies, code patterns, and documentation to create a detailed context file that helps AI reviewers understand:

- **Project Overview**: Purpose, domain, and key characteristics
- **Technology Stack**: Dependencies, frameworks, and tools with versions
- **Architecture**: Code organization, patterns, and design principles  
- **Review Focus**: Areas that deserve special attention during code review

## Installation & Setup

The context generator is included with `ai-code-review`. No additional installation needed.

### Prerequisites

- **Git Repository**: The project must be a Git repository with committed files
- **Git Command**: Git must be installed and available in PATH
- The context generator analyzes **only Git-tracked files** (files added to Git)
- Untracked files and files in `.gitignore` are not analyzed

### Configuration

You can configure the context generator using:

1. Environment variables (via `.env` file)
2. Command-line options

#### Environment Variables

Create a `.env` file in your project root:

```bash
# AI Provider Configuration
AI_PROVIDER=anthropic              # or gemini, ollama
AI_API_KEY=your_api_key_here
AI_MODEL=claude-sonnet-4-20250514
AI_MAX_TOKENS=8000

# Context Generator Settings
CONTEXT_OUTPUT_PATH=.ai_review/project.md
```

#### Supported AI Providers

- **Anthropic Claude**: `anthropic` (requires `ANTHROPIC_API_KEY`)
- **Google Gemini**: `gemini` (requires `GEMINI_API_KEY`)
- **Ollama**: `ollama` (local models, no API key needed)

## Usage

### Basic Usage

```bash
# Generate complete context for current directory
ai-generate-context .

# Specify output file
ai-generate-context . --output .ai_review/project.md

# Use specific AI provider
ai-generate-context . --provider anthropic --ai-api-key your-key

# Dry run (no LLM calls, shows what would be generated)
ai-generate-context . --dry-run
```

### Partial Updates

Update only specific sections while preserving manual content:

```bash
# Update only technology stack
ai-generate-context . --section tech_stack

# Update multiple sections
ai-generate-context . --section overview --section structure

# Available sections: overview, tech_stack, structure, review_focus
```

### Advanced Options

```bash
# Use different AI model
ai-generate-context . --ai-model claude-sonnet-4-20250514

# Adjust token limit
ai-generate-context . --max-tokens 4000

# Verbose output
ai-generate-context . --verbose
```

## Generated Sections

### Automatic Sections

These sections are generated automatically by analyzing your project:

#### Project Overview

- **Purpose**: Detected from README.md, package.json, pyproject.toml
- **Type**: Inferred from project structure (CLI, web app, library, etc.)
- **Domain**: Categorized based on dependencies and code patterns
- **Key Dependencies**: Most important libraries for understanding the codebase

#### Technology Stack

- **Core Technologies**: Programming languages, frameworks, runtime environments
- **Key Dependencies**: Critical libraries with versions and brief explanations
- **Development Tools**: Testing frameworks, linters, build tools, CI/CD

#### Architecture & Code Organization

- **Project Structure**: Directory tree with important files highlighted
- **Design Patterns**: Detected architectural patterns and principles
- **Code Organization**: Module structure and separation of concerns

#### Review Focus Areas

- **Generated Focus Points**: Based on technology stack and detected patterns
- **Common Issues**: Technology-specific things to watch for
- **Best Practices**: Framework and language-specific guidelines

### Manual Sections

These sections are preserved across updates and should be filled manually:

#### Business Logic & Implementation Decisions

Document unusual patterns, architectural decisions, and domain-specific logic:

```markdown
### Business Logic & Implementation Decisions

- calculate_vat() complexity is required by EU tax regulations
- Deliberate N+1 queries in reporting endpoints due to data freshness requirements  
- Long functions in data_migrations.py are acceptable (one-time transformation scripts)
- Custom retry logic in payment_processor.py handles bank API quirks
```

#### Domain-Specific Context

Information about internal services, external dependencies, and domain terminology:

```markdown
### Domain-Specific Context

- Internal APIs: UserService runs on internal-api.company.com:8080
- Message Queue: Uses company RabbitMQ cluster (connection strings in K8s ConfigMap)
- External Services: Stripe for payments, SendGrid for emails, Auth0 for authentication
- Database: PostgreSQL with read replicas (don't suggest caching for reports)
```

#### Special Cases & Edge Handling

Document exceptions, legacy requirements, and intentional "anti-patterns":

```markdown
### Special Cases & Edge Handling

- LOG_LEVEL=DEBUG in production is intentional for compliance logging
- time.sleep() in tests is necessary for rate-limiting integration tests  
- `# noqa` comments are legitimate for SQLAlchemy dynamic attributes
- UserRole.SUPER_ADMIN bypass checks are audited and approved by security
```

## Best Practices

### Workflow Recommendations

1. **Start with automation**: Generate initial context with `ai-generate-context`
2. **Add manual context**: Fill in business logic and domain-specific information
3. **Commit to repository**: Add `.ai_review/project.md` to Git so CI/CD and team can use it
4. **Keep dependencies current**: Use `--section tech_stack` to update technical details
5. **Preserve manual work**: Manual sections are automatically preserved during updates

### What to Keep Manual

Focus manual sections on information that can't be automatically detected:

- **Business rules** that aren't evident from code structure
- **External service details** not visible in your repository
- **Deployment and infrastructure** considerations
- **Legacy compatibility** requirements and constraints
- **Domain-specific terminology** and internal service names
- **Intentional deviations** from best practices with business justification

### What to Keep Automatic

Let the generator handle technical details that change frequently:

- **Dependency versions** and descriptions
- **Project structure** and file organization
- **Framework-specific** review focus areas
- **Technology stack** details and configurations

### Integration Patterns

#### Development Workflow

```bash
# During active development
ai-generate-context . --section tech_stack  # Keep deps current
```

#### CI/CD Integration

#### Don't generate context in CI/CD pipelines

The context generator should be used **locally** to create and maintain the context file. The CI/CD pipeline should **use** the existing context file, not generate it.

**✅ Correct workflow:**
1. **Local**: Generate/update context with `ai-generate-context`
2. **Local**: Review and customize the generated context
3. **Local**: Commit `.ai_review/project.md` to your repository
4. **CI/CD**: The `ai-code-review` tool automatically uses the committed context file

#### Team Onboarding

```bash
# For new team members
ai-generate-context . --output onboarding-context.md
```

## File Structure

The generated context file follows this structure:

```markdown
# Project Context for AI Code Review

## Project Overview
<!-- Automatically generated -->

## Technology Stack
<!-- Automatically generated -->

## Architecture & Code Organization  
<!-- Automatically generated -->

## Review Focus Areas
<!-- Automatically generated -->

<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->

### Business Logic & Implementation Decisions
<!-- Manual content preserved here -->

### Domain-Specific Context
<!-- Manual content preserved here -->

### Special Cases & Edge Handling
<!-- Manual content preserved here -->
```

## Troubleshooting

### Common Issues

#### "No Git repository found" or "No tracked files"

```bash
# Make sure you're in a Git repository
git status

# If not a Git repo, initialize it
git init
git add .
git commit -m "Initial commit"

# If files aren't tracked, add them to Git
git add your-files
git commit -m "Add files for analysis"
```

#### "No API key provided"

```bash
# Set API key in environment
export ANTHROPIC_API_KEY=your_key_here
ai-generate-context .

# Or use command line option
ai-generate-context . --ai-api-key your_key_here
```

#### "Context file too large"

```bash
# Reduce token limit
ai-generate-context . --max-tokens 4000

# Use more efficient model
ai-generate-context . --ai-model claude-sonnet-4-20250514
```

#### "Manual sections disappeared"

- Check that your manual content is below the `<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->` marker
- Don't remove or modify the marker line
- Manual content above the marker will be lost during updates

### Debug Mode

```bash
# Enable verbose logging
ai-generate-context . --verbose

# Dry run to see what would be generated
ai-generate-context . --dry-run
```

## Integration with AI Code Review

The context generator is designed to work seamlessly with the main `ai-code-review` tool:

### Environment Variable Control

- **Enable**: `ENABLE_PROJECT_CONTEXT=true` (default if `.ai_review/project.md` exists)
- **Disable**: `ENABLE_PROJECT_CONTEXT=false` or `--no-project-context` flag
- **File location**: Must be exactly `.ai_review/project.md` in your repository root

### Workflow Integration

**Local Development Workflow:**

1. **Generate context**: `ai-generate-context . --output .ai_review/project.md`
2. **Review and customize**: Edit the manual sections in `.ai_review/project.md`
3. **Commit to repository**: `git add .ai_review/project.md && git commit -m "Add project context"`
4. **CI/CD automatically uses it**: The `ai-code-review` tool reads the committed context file
5. **Keep updated**: Periodically update with `ai-generate-context . --section tech_stack`

**Important**: The context file should be **committed to your repository** so that CI/CD pipelines and team members can use the same context.

## Examples

See `.ai_review/project.md` for a real example of a comprehensive context file with both automatic and manual sections filled in. This file is actively used for AI code reviews of this project.

## Supported Project Types

The context generator works with any Git repository but has enhanced support for:

- **Python**: pyproject.toml, requirements.txt, setup.py
- **Node.js**: package.json, yarn.lock, npm-shrinkwrap.json
- **Ruby**: Gemfile, gemspec files
- **Go**: go.mod, go.sum
- **Rust**: Cargo.toml, Cargo.lock
- **Java**: pom.xml, build.gradle
- **PHP**: composer.json

**Important**: Only **Git-tracked files** are analyzed. Make sure your project files are committed to Git before running the context generator.

For other project types, it falls back to generic file analysis and structure detection based on the tracked files.
