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
  - [Context7 Integration](#context7-integration)
  - [CI/CD Documentation Integration](#cicd-documentation-integration)
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

# Context7 Integration (Optional)
CONTEXT7_API_KEY=your_context7_api_key_here
```

#### Supported AI Providers

- **Anthropic Claude**: `anthropic` (requires `AI_API_KEY`)
- **Google Gemini**: `gemini` (requires `AI_API_KEY`)
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

# Enable Context7 integration for library documentation
ai-generate-context . --enable-context7

# Context7 with specific libraries
ai-generate-context . --enable-context7 --context7-libraries "fastapi,pydantic,sqlalchemy"

# Context7 with custom token limit per library
ai-generate-context . --enable-context7 --context7-max-tokens 1500
```

### Context7 Integration

Context7 integration enhances AI code reviews by fetching official library documentation for your project's dependencies. This provides the LLM with authoritative information about APIs, best practices, and recommended usage patterns.

#### Context7 Prerequisites

- Context7 API key (sign up at <https://context7.com>)
- `aiohttp` Python package (usually already installed)
- Project must have identifiable dependencies (e.g., `requirements.txt`, `pyproject.toml`, `package.json`)

#### Getting Context7 API Access

Context7 integration uses the Context7 REST API to fetch official library documentation. No additional software installation is required.

**Important**: You need a Context7 API key to use this feature.

**How to Get API Access:**

1. **Sign up**: Visit <https://context7.com> and create an account
2. **Get API Key**: Generate your API key from the dashboard
3. **Set Environment Variable**: Add to your `.env` file:
   ```bash
   CONTEXT7_API_KEY=your_api_key_here
   ```

#### Configuration Options

You can configure Context7 integration in your `.ai_review/config.yml` file:

```yaml
context7:
  enabled: true
  max_libraries: 3
  max_tokens_per_library: 2000
  timeout_seconds: 10
  priority_libraries:
    - fastapi
    - pydantic
    - sqlalchemy
    - requests
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable Context7 integration |
| `max_libraries` | integer | `3` | Maximum number of libraries to fetch documentation for |
| `max_tokens_per_library` | integer | `2000` | Maximum tokens to fetch per library (100-10000) |
| `timeout_seconds` | integer | `10` | Timeout for Context7 API calls (1-60 seconds) |
| `priority_libraries` | list | `[]` | Specific libraries to fetch documentation for |

#### How It Works

1. **Dependency Detection**: Context7 analyzes your project to identify dependencies
2. **Library Selection**: Selects important libraries based on priority list or built-in heuristics
3. **Documentation Fetching**: Retrieves official documentation for selected libraries in parallel
4. **LLM Enhancement**: Provides documentation context to the LLM for enhanced analysis

#### Library Selection

**Priority Libraries**: If you specify `priority_libraries`, Context7 will only fetch documentation for those libraries that are present in your project dependencies.

**Auto-Detection**: If no priority libraries are specified, Context7 uses built-in heuristics to identify important libraries:

- **Web Frameworks**: fastapi, django, flask, starlette
- **Data & ORM**: sqlalchemy, pydantic, pandas, numpy
- **HTTP Clients**: requests, aiohttp, httpx
- **Testing**: pytest, unittest
- **Cloud & Infrastructure**: boto3, kubernetes, docker
- **ML & AI**: tensorflow, pytorch, scikit-learn, langchain

#### Example Configurations

**Web API Project:**
```yaml
context7:
  enabled: true
  priority_libraries:
    - fastapi
    - pydantic
    - sqlalchemy
    - uvicorn
    - requests
```

**Data Science Project:**
```yaml
context7:
  enabled: true
  priority_libraries:
    - pandas
    - numpy
    - scikit-learn
    - matplotlib
    - jupyter
```

**Django Project:**
```yaml
context7:
  enabled: true
  priority_libraries:
    - django
    - djangorestframework
    - celery
    - redis
    - psycopg2
```

### CI/CD Documentation Integration

The context generator can automatically fetch and analyze official CI/CD documentation for projects using GitLab CI or GitHub Actions. This feature is **disabled by default** to reduce token consumption, as CI/CD documentation can be quite extensive.

#### When to Enable CI/CD Documentation

Enable this feature only for projects that **heavily rely on CI/CD configuration**:

- ✅ Projects with complex multi-stage pipelines
- ✅ Projects using advanced CI/CD features (rules, dynamic pipelines, matrix builds)
- ✅ Projects where CI/CD configuration changes frequently
- ✅ Teams that need to review CI/CD configuration changes regularly

**Do NOT enable** for:

- ❌ Simple projects with basic CI/CD setup
- ❌ Projects where CI/CD rarely changes
- ❌ Token-constrained environments

#### CI/CD Prerequisites

- Project must have CI/CD configuration files:
  - **GitLab CI**: `.gitlab-ci.yml`
  - **GitHub Actions**: `.github/workflows/*.yml`
- Internet connection to fetch official documentation
- No API key required (fetches from public repositories)

#### CI/CD Configuration Options

**Via `.env` file:**
```bash
# Enable CI/CD documentation fetching (default: false)
ENABLE_CI_DOCS=true
```

**Via `.ai_review/config.yml` file:**
```yaml
ci_docs:
  enabled: true
  timeout_seconds: 30         # Timeout for HTTP requests (default: 30)
  max_content_length: 200000  # Maximum content length per document (default: 200K, truncates if exceeded)
```

**Via command-line:**
```bash
# Enable for specific generation
ai-generate-context . --enable-ci-docs

# Explicitly disable (default)
ai-generate-context . --disable-ci-docs
```

#### CI/CD Documentation Process

1. **CI System Detection**: Automatically detects GitLab CI or GitHub Actions from configuration files
2. **Documentation Fetching**: Retrieves official YAML syntax documentation directly from source repositories
3. **LLM Analysis**: Analyzes documentation to extract recent changes, deprecations, and critical updates
4. **Context Integration**: Adds a focused "CI/CD Recent Changes & Critical Updates" section to the generated context

#### What's Included

The generated CI/CD section focuses on **recent changes and critical updates** that LLMs need for accurate code reviews:

- **Recent Changes & New Features**: New keywords, syntax, or capabilities introduced in the last 2-3 years
- **Deprecated & Removed Features**: What no longer works and how to migrate
- **Security Updates & Vulnerabilities**: Recent security changes and common misconfigurations
- **Breaking Changes & Migration Issues**: Configuration changes that break existing setups
- **Common Configuration Errors**: Specific mistakes that cause pipeline failures

#### Supported CI/CD Systems

| System | Configuration File(s) | Documentation Source |
|--------|----------------------|---------------------|
| **GitLab CI** | `.gitlab-ci.yml` | Official GitLab repository |
| **GitHub Actions** | `.github/workflows/*.yml` | Official GitHub docs repository |

#### Example Configuration

**For CI-Heavy Projects:**
```yaml
# .ai_review/config.yml
ci_docs:
  enabled: true
  timeout_seconds: 30
  max_content_length: 200000  # Can be increased if documentation is very large

context7:
  enabled: true
  max_libraries: 3
```

**For Standard Projects (Recommended):**
```yaml
# .ai_review/config.yml
ci_docs:
  enabled: false  # Keep disabled to save tokens

context7:
  enabled: true
  max_libraries: 3
```

#### Token Consumption

CI/CD documentation is now highly focused on recent changes:

- **GitLab CI**: ~2,000-3,000 tokens for recent changes guide
- **GitHub Actions**: ~1,500-2,500 tokens for recent changes guide

**Recommendation**: Enable this feature if your project uses advanced CI/CD features or needs to stay current with recent changes and deprecations.

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

#### Context7 Library Documentation (Optional)

When Context7 integration is enabled, this section provides:
- **Official API Documentation**: Authoritative information from library maintainers
- **Usage Patterns**: Recommended ways to use important dependencies
- **Best Practices**: Library-specific guidelines and common patterns
- **Integration Guidelines**: How libraries should work together in your project

### Manual Sections

These sections are preserved across updates and should be filled manually:

#### Business Logic & Implementation Decisions

Document unusual patterns, architectural decisions, and domain-specific logic:

```markdown
## Business Logic & Implementation Decisions

- calculate_vat() complexity is required by EU tax regulations
- Deliberate N+1 queries in reporting endpoints due to data freshness requirements
- Long functions in data_migrations.py are acceptable (one-time transformation scripts)
- Custom retry logic in payment_processor.py handles bank API quirks
```

#### Domain-Specific Context

Information about internal services, external dependencies, and domain terminology:

```markdown
## Domain-Specific Context

- Internal APIs: UserService runs on internal-api.company.com:8080
- Message Queue: Uses company RabbitMQ cluster (connection strings in K8s ConfigMap)
- External Services: Stripe for payments, SendGrid for emails, Auth0 for authentication
- Database: PostgreSQL with read replicas (don't suggest caching for reports)
```

#### Special Cases & Edge Handling

Document exceptions, legacy requirements, and intentional "anti-patterns":

```markdown
## Special Cases & Edge Handling

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

## Context7 Library Documentation
<!-- Automatically generated when Context7 is enabled -->

<!-- MANUAL SECTIONS - DO NOT MODIFY THIS LINE -->

## Business Logic & Implementation Decisions
<!-- Manual content preserved here -->

## Domain-Specific Context
<!-- Manual content preserved here -->

## Special Cases & Edge Handling
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

### Context7 Issues

#### Missing API Key

If you see warnings like:
```
WARNING: Context7 API key not available library=fastapi
INFO: Context7 section skipped - no documentation available
```

**Cause**: Missing or invalid Context7 API key.

**Solution**: Set your API key in the environment:
```bash
export CONTEXT7_API_KEY=your_api_key_here
# or add to .env file
echo "CONTEXT7_API_KEY=your_api_key_here" >> .env
```

#### Context7 Performance Issues

If Context7 integration is slow:

1. Reduce `max_tokens_per_library` (e.g., to 1000)
2. Decrease `timeout_seconds` (e.g., to 5)
3. Specify fewer `priority_libraries`
4. Check your internet connection

#### No Documentation Found

If no Context7 documentation is fetched:

1. Verify your project has recognizable dependencies
2. Check that priority libraries are correctly spelled
3. Try with well-known libraries (e.g., fastapi, requests)
4. Ensure Context7 service is available

#### Expected Behavior

If Context7 API is not available, the integration gracefully degrades:

- ✅ Context generation continues normally
- ✅ All other sections work as expected
- ⚠️ Warning messages appear (this is informational, not an error)
- ❌ No Context7 documentation section is generated

**This is the intended behavior** - Context7 is optional and won't break your workflow.

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

**Context7 Integration**: Works with any project type that has recognizable dependencies. Context7 automatically detects important libraries from your dependency files and fetches official documentation to enhance code reviews.

For other project types, it falls back to generic file analysis and structure detection based on the tracked files.
