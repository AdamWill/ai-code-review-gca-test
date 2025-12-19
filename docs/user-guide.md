# User Guide: AI Code Review

Simple guide to get AI-powered code reviews with **3 powerful workflows**:

- 🔍 **Local Reviews** - Review your changes before committing
- 🌐 **Remote Reviews** - Analyze existing MRs/PRs from terminal
- 🤖 **CI Integration** - Automated reviews in CI/CD pipelines

## 📑 Table of Contents

- [🔍 Local Code Reviews](#-local-code-reviews)
  - [Local Setup](#local-setup)
  - [Local Basic Usage](#local-basic-usage)
  - [Advanced Local Options](#advanced-local-options)
- [🌐 Remote Code Reviews](#-remote-code-reviews)
  - [Prerequisites](#prerequisites)
  - [Remote Usage Examples](#remote-usage-examples)
  - [Output Options](#output-options)
  - [Local Development Workflow](#local-development-workflow)
- [🤖 CI Integration](#-ci-integration)
  - [GitLab CI/CD (Pre-built Container)](#gitlab-cicd-pre-built-container)
  - [GitHub Actions (Using GitLab Container)](#github-actions-using-gitlab-container)
  - [Build Your Own Container](#build-your-own-container)
  - [Install from Repository](#install-from-repository)
- [⚙️ Advanced Configuration](#️-advanced-configuration)
  - [📄 YAML Configuration Files](#-yaml-configuration-files)
  - [CI/CD Variables Configuration](#cicd-variables-configuration)
  - [🚀 Smart Skip Review](#-smart-skip-review)
  - [SSL Configuration for Internal GitLab Instances](#ssl-configuration-for-internal-gitlab-instances)
  - [🎯 Project Context Configuration](#-project-context-configuration)
  - [👥 Team/Organization Context](#-teamorganization-context)
  - [🧠 Intelligent Review Context (Two-Phase Synthesis)](#-intelligent-review-context-two-phase-synthesis)
  - [📝 Review Format Configuration](#-review-format-configuration)
- [🔧 Timeout Configuration](#-timeout-configuration)
  - [How It Works](#how-it-works)
  - [Benefits](#benefits)
  - [Advanced Configuration](#advanced-configuration-1)
- [🔧 Troubleshooting](#-troubleshooting)
  - [Common Issues](#common-issues)
  - [SSL Certificate Errors](#ssl-certificate-errors)
  - [Debug Mode](#debug-mode)
- [📚 More Information](#-more-information)

## 🔍 Local Code Reviews

Review your **local Git changes** before committing. No platform tokens required!

### Local Setup

#### ption 1: Ollama (Completely Local - Recommended)

```bash
# Install and start Ollama
ollama serve
ollama pull qwen2.5-coder:7b

# Review from any git repository
cd your-git-project
ai-code-review --local
```

#### Option 2: Cloud AI Providers

```bash
# Gemini (recommended for production)
export AI_API_KEY=your_gemini_api_key
ai-code-review --local --ai-provider gemini

# Anthropic Claude
export AI_API_KEY=your_anthropic_api_key
ai-code-review --local --ai-provider anthropic
```

### Local Basic Usage

```bash
# Review current changes vs main
ai-code-review --local

# Review vs different target branch
ai-code-review --local --target-branch develop

# Save review (simple format, no collapsible sections)
ai-code-review --local -o local-review.md

# Dry run (no AI costs)
ai-code-review --local --dry-run
```

### Advanced Local Options

```bash
# Custom model and file limits
ai-code-review --local \
  --ai-model qwen2.5-coder:14b \
  --max-files 10 \
  --max-file-context 2000

# Specific language hint
ai-code-review --local --language-hint "Python web API"

# Exclude specific files
ai-code-review --local --exclude-files "**/test_*,**/*lock*"
```

## 🌐 Remote Code Reviews

Analyze existing MRs/PRs from your terminal.

### Prerequisites

Before running remotely, ensure you have:

1. **Platform Access Token**: GitLab Personal Access Token or GitHub Token
2. **AI API Key**: API key for your chosen AI provider (Gemini, Anthropic, or local Ollama)
3. **Project Access**: Read access to the GitLab project or GitHub repository

### Remote Usage Examples

#### 1. Analyze Existing MRs/PRs (No Posting)

```bash
# GitLab MR analysis
AI_API_KEY=your_key ai-code-review group/project 123

# GitHub PR analysis
AI_API_KEY=your_key ai-code-review --platform github owner/repo 456

# With custom settings
ai-code-review group/project 123 \
  --language-hint python \
  --exclude-files "**/*test*" \
  --big-diffs

# Code-focused review (without MR Summary section)
ai-code-review group/project 123 --no-mr-summary
```

#### 2. Post Review as Comment

```bash
# GitLab MR - post review
AI_API_KEY=your_key ai-code-review group/project 123 --post

# GitHub PR - post review
AI_API_KEY=your_key ai-code-review --platform github owner/repo 456 --post
```

## 🤖 CI Integration

### GitLab CI/CD (Pre-built Container)

Add this job to your `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - code-review

ai-code-review:
  stage: code-review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY   # Set as protected/masked variable
  script:
    - ai-code-review --post
  allow_failure: true  # Don't block MRs if review fails
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### GitHub Actions (Using GitLab Container)

Add this workflow to `.github/workflows/ai-review.yml`:

```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    # ⚠️ IMPORTANT: Add write permissions for PR comments
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
        run: |
          ai-code-review --pr-number ${{ github.event.pull_request.number }} --post
```

**Setup Requirements:**

**Note:** The platform (GitLab/GitHub) is **automatically detected** from CI/CD environment variables. No need to specify `--platform` in workflows!

1. **Create Platform Access Token:**

**For GitLab:**
- Go to GitLab → **Settings → Access Tokens**
- Create token with scope: `api`, `read_user`, `read_repository`
- Copy the generated token (starts with `glpat_`)

**For GitHub:**
- Go to GitHub → **Settings → Developer Settings → Personal Access Tokens → Tokens (classic)**
- Create token with scopes: `repo`, `read:org`
- Copy the generated token (starts with `ghp_`)

1. **Configure CI/CD Variables:**

**For GitLab CI/CD:**
- In your project: **Settings → CI/CD → Variables**
- Add `GITLAB_TOKEN` as **Protected + Masked** variable (your GitLab token)
- Add `GEMINI_API_KEY` as **Protected + Masked** variable
- Get your Gemini key from: <https://makersuite.google.com/app/apikey>

**For GitHub Actions:**
- In your repository: **Settings → Secrets and Variables → Actions**
- Add `GITHUB_TOKEN` (automatically available, no need to set manually)
- Add `GEMINI_API_KEY` as **Repository Secret**
- Get your Gemini key from: <https://makersuite.google.com/app/apikey>

### Build Your Own Container

Create your own container and publish to your registry:

#### 3.1. Use Project's Containerfile

Use the existing `Containerfile` from the project:

```dockerfile
# Build a binary distributable out of ai-code-review
FROM quay.io/automotive-toolchain/python3-uv:latest as builder
WORKDIR /code
COPY pyproject.toml uv.lock README.md ./
COPY src src
RUN uv build --no-cache

# Use the binary distributable in the system Python environment
# so it's accessible globally in containers
FROM registry.access.redhat.com/ubi9:latest
ENV DNF_OPTS="--setopt=install_weak_deps=False --setopt=tsflags=nodocs"
RUN dnf install -y \
                python3.12-pip \
 && dnf clean all -y
COPY --from=builder /code/dist/*.whl /tmp/
RUN pip3.12 install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
```

#### 3.2. Build and Push

```bash
# Build container
podman build -t $CI_REGISTRY_IMAGE/ai-review:latest .

# Push to your registry
podman push $CI_REGISTRY_IMAGE/ai-review:latest
```

#### 3.3. Use in CI/CD

```yaml
ai-code-review:
  stage: code-review
  image: $CI_REGISTRY_IMAGE/ai-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Install from Repository

Install directly from the repository in your CI job:

#### GitLab Installation

```yaml
ai-code-review:
  stage: code-review
  image: python:3.12-slim
  variables:
    AI_API_KEY: $GEMINI_API_KEY
  before_script:
    # Install from GitLab repository (not published on PyPI yet)
    - pip install git+https://gitlab.com/redhat/edge/ci-cd/ai-code-review.git
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

#### GitHub Installation (Alternative Method)

```yaml
name: AI Code Review (Install from Source)
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install from repository
        run: |
          pip install git+https://gitlab.com/redhat/edge/ci-cd/ai-code-review.git
      - name: Run AI Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          AI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          ai-code-review --pr-number ${{ github.event.pull_request.number }} --post
```

**Note:** Using the GitLab container image (Option 2) is **recommended** as it's faster and more reliable than installing from source.

**Why use the GitLab container image?**
- ✅ **Faster execution** - Pre-built image, no installation time
- ✅ **Same environment** - Identical to GitLab CI/CD usage
- ✅ **No PyPI dependency** - Package not yet published on PyPI
- ✅ **Public access** - GitLab registry image is publicly accessible

**Note:** The package is not yet published on PyPI, so you must either use the container image or install from the GitLab repository.

## ⚙️ Advanced Configuration

### 📄 YAML Configuration Files

Starting from v1.7.0+, you can use YAML configuration files for easier project setup and team consistency. Configuration files complement environment variables and CLI arguments with a clear priority system.

#### Configuration Priority Order

1. **CLI Arguments** (highest priority) - `--ai-provider gemini`
2. **Environment Variables** - `AI_PROVIDER=gemini`
3. **YAML Configuration File** - `ai_provider: gemini`
4. **Default Values** (lowest priority)

#### Quick Setup

**1. Create configuration directory and file:**

```bash
# Create configuration directory
mkdir -p .ai_review

# Copy example configuration
cp .ai_review/config.yml.example .ai_review/config.yml

# Edit for your project needs
vim .ai_review/config.yml
```

**2. The tool auto-detects `.ai_review/config.yml` in your project root:**

```bash
# Uses .ai_review/config.yml automatically
ai-code-review group/project 123

# Skip config file loading
ai-code-review group/project 123 --no-config-file

# Use custom config file
ai-code-review group/project 123 --config-file my-config.yml
```

#### Configuration Examples

**Basic GitLab Setup:**

```yaml
# .ai_review/config.yml
platform_provider: gitlab
gitlab_url: https://gitlab.com
ai_provider: gemini
ai_model: gemini-3-pro-preview
max_files: 50
include_mr_summary: true

# Exclude common noise files
exclude_patterns:
  - "*.lock"
  - "node_modules/**"
  - "dist/**"
  - "__pycache__/**"
```

**Local Development with Ollama:**

```yaml
# .ai_review/config.yml - Local development setup
platform_provider: local
ai_provider: ollama
ai_model: qwen2.5-coder:7b
ollama_base_url: http://localhost:11434
target_branch: main
log_level: INFO
```

**GitHub + Anthropic Setup:**

```yaml
# .ai_review/config.yml - GitHub with Claude
platform_provider: github
github_url: https://api.github.com
ai_provider: anthropic
ai_model: claude-sonnet-4-20250514
temperature: 0.1
max_tokens: 4000
```

**Self-hosted GitLab with SSL:**

```yaml
# .ai_review/config.yml - Internal GitLab
platform_provider: gitlab
gitlab_url: https://gitlab.company.com
ssl_verify: true
ssl_cert_path: /etc/ssl/certs/company-ca.pem
ai_provider: gemini
ai_model: gemini-3-pro-preview

# Project context
enable_project_context: true
project_context_file: .ai_review/project.md
```

#### Security Best Practices

**❌ DO NOT store sensitive tokens in YAML files:**

```yaml
# BAD - tokens in config file (security risk)
gitlab_token: glpat_xxxxxxxxxxxxxxxxxxxx
ai_api_key: your_secret_api_key
```

**✅ Use environment variables for secrets:**

```yaml
# GOOD - config file without secrets
platform_provider: gitlab
ai_provider: gemini
# Tokens loaded from environment variables
```

```bash
# Secrets in environment (.env file or shell)
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
export AI_API_KEY=your_gemini_api_key
```

#### Available Configuration Options

See the [complete example file](../.ai_review/config.yml.example) for all available options including:

- Platform settings (GitLab/GitHub/Local URLs and options)
- AI provider settings (models, parameters, timeouts)
- Processing limits (max files, max characters, big diff handling)
- File filtering (exclude patterns for noise reduction)
- Project context and review format options
- SSL/TLS settings for internal instances
- Development options (dry-run, logging levels)

### CI/CD Variables Configuration

#### GitLab CI/CD Variables

Set these in **Settings → CI/CD → Variables**:

```bash
# GitLab Access (set as Protected + Masked in project variables)
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx

# AI Provider (set as Protected + Masked in project variables)
GEMINI_API_KEY=your_google_gemini_api_key_here   # For Gemini
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here    # For Anthropic
```

**Note:** `GITLAB_TOKEN` is automatically available in CI/CD jobs when set as project variable.

#### GitHub Actions Secrets

Set these in **Settings → Secrets and Variables → Actions**:

```bash
# GitHub Access (automatically available as GITHUB_TOKEN)
# No manual setup needed - GitHub provides this automatically

# AI Provider (set as Repository Secret)
GEMINI_API_KEY=your_google_gemini_api_key_here   # For Gemini
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here    # For Anthropic
```

**Important:** `GITHUB_TOKEN` is automatically provided by GitHub Actions, but requires explicit `permissions` in the workflow (see example above). If the automatic token doesn't work in your organization:

1. **Check repository settings**: Go to Settings → Actions → General → Workflow permissions
2. **Option A**: Enable "Read and write permissions" for `GITHUB_TOKEN`
3. **Option B**: Create a Personal Access Token with `repo` scope and add it as `PERSONAL_TOKEN` secret:
   ```yaml
   env:
     GITHUB_TOKEN: ${{ secrets.PERSONAL_TOKEN }}  # Use custom PAT instead
   ```

#### Optional Configuration Variables

```bash
# AI Configuration
AI_PROVIDER=gemini              # gemini, anthropic (cloud providers only for CI/CD - no local models)
AI_MODEL=gemini-3-pro-preview   # Model name (gemini-3-pro-preview, claude-sonnet-4-20250514)
TEMPERATURE=0.1                 # Response randomness (0.1 default)
MAX_TOKENS=8000                 # Max response tokens (8000 default)

# Processing Configuration
MAX_CHARS=100000               # Max diff characters (100K default)
MAX_FILES=100                  # Max files to process (100 default)
BIG_DIFFS=false                # Force 24K context (false default)
LANGUAGE_HINT=python           # Language hint for better analysis

# Project Context
ENABLE_PROJECT_CONTEXT=true    # Load project context from .ai_review/project.md (default: true)
PROJECT_CONTEXT_FILE=.ai_review/project.md  # Path to project context file (default: .ai_review/project.md)

# Review Format
INCLUDE_MR_SUMMARY=true        # Include MR Summary section in reviews (default: true)

# File Filtering
EXCLUDE_PATTERNS="*.lock,*.min.js,node_modules/**,dist/**"

# Logging
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### ⏱️ Timeout and Retry Configuration

For CI/CD environments, timeout and retry settings are designed to **fail fast** rather than blocking pipelines:

#### Default Settings (Optimized for CI/CD)

```bash
LLM_TIMEOUT=60         # Default: 60 seconds (1 minute)
LLM_MAX_RETRIES=2      # Default: 2 retries
```

These defaults mean:
- **First attempt**: 60 seconds max
- **Retry 1**: 60 seconds max (if first fails)
- **Retry 2**: 60 seconds max (if retry 1 fails)
- **Total maximum wait**: ~3 minutes (60s × 3 attempts)

#### Why These Defaults?

⚡ **Fast failures**: Jobs fail quickly on server issues (1-3 minutes max)
- Prevents 20+ minute waits on server timeouts (like 504 errors)
- CI/CD pipelines don't get blocked indefinitely
- 60s is 2x the minimum needed for Claude (30s)

🔄 **Retry friendly**: Failed jobs can be manually retried
- Lower retry counts mean faster failure detection
- Manual retry in GitLab/GitHub is fast and easy

🚫 **No blocking**: Prevents pipeline delays
- `allow_failure: true` in CI config means reviews don't block merges
- Failed review jobs can be investigated separately

#### Example: Handling Server Errors

**Scenario**: Gemini API returns 504 timeout errors

❌ **Without timeout configuration** (old behavior):
```
14:00:00 → Start
14:10:00 → Retry 1 (after 10 min wait)
14:20:00 → Retry 2 (after 10 min wait)
14:30:00 → Finally completes or fails
Total: 30+ minutes blocking the pipeline
```

✅ **With default timeout configuration** (new behavior):
```
14:00:00 → Start
14:01:00 → Retry 1 (after 1 min timeout)
14:02:00 → Retry 2 (after 1 min timeout)
14:03:00 → Fails fast and exits
Total: ~3 minutes, job can be retried manually
```

#### Custom Configuration

##### For Slow Networks or Large Diffs

```bash
# Environment variables
LLM_TIMEOUT=120        # 2 minutes per attempt
LLM_MAX_RETRIES=3      # 3 retries (total: ~8 min max)

# Config file (.ai_review/config.yml)
llm_timeout: 120
llm_max_retries: 3
```

##### For Ultra-Fast Failure (Aggressive CI/CD)

```bash
# Environment variables
LLM_TIMEOUT=30         # 30 seconds per attempt
LLM_MAX_RETRIES=1      # Only 1 retry (total: ~1 min max)

# Config file (.ai_review/config.yml)
llm_timeout: 30
llm_max_retries: 1
```

##### For Local Development (More Patient)

```bash
# Environment variables
LLM_TIMEOUT=180        # 3 minutes per attempt
LLM_MAX_RETRIES=5      # 5 retries (total: ~18 min max)

# Config file (.ai_review/config.yml)
llm_timeout: 180
llm_max_retries: 5
```

#### Configuration Methods

##### Method 1: Environment Variables (Recommended for CI/CD)

```yaml
# .gitlab-ci.yml
ai-review:
  variables:
    LLM_TIMEOUT: "60"
    LLM_MAX_RETRIES: "2"
```

```yaml
# .github/workflows/ai-review.yml
- name: Run AI Review
  env:
    LLM_TIMEOUT: 60
    LLM_MAX_RETRIES: 2
```

##### Method 2: Config File (Recommended for Project Defaults)

```yaml
# .ai_review/config.yml
llm_timeout: 60
llm_max_retries: 2
```

##### Method 3: .env File (Local Development)

```bash
# .env
LLM_TIMEOUT=120
LLM_MAX_RETRIES=3
```

#### Best Practices

1. **CI/CD Environments**:
   - Use default values (60s timeout, 2 retries)
   - Set `allow_failure: true` in CI config
   - Enable manual retry for failed jobs

2. **Local Development**:
   - Increase timeout for complex reviews (120-180s)
   - Increase retries for unreliable networks (3-5)

3. **Production/Critical Reviews**:
   - Monitor for frequent timeouts
   - Investigate server-side issues (API status pages)
   - Consider switching AI providers if timeouts persist

4. **Cost Optimization**:
   - Lower timeouts reduce wasted API call time
   - Fewer retries reduce duplicate API calls on permanent failures

### 🚀 Smart Skip Review

The **Skip Review mechanism** automatically detects and skips unnecessary AI reviews to reduce noise, save API costs, and speed up CI/CD pipelines.

#### How It Works

The tool uses **multiple detection criteria** in priority order:

1. **🏷️ Keywords** - Explicit tags in PR/MR titles or descriptions
2. **🎭 Regex Patterns** - Automated commit message patterns
3. **📝 Documentation Patterns** - Documentation-only change patterns (if enabled)
4. **🤖 Bot Authors** - Known automation accounts
5. **📚 File Analysis** - Documentation-only file changes

#### Default Configuration

Skip Review is **enabled by default** with these settings:

```yaml
# .ai_review/config.yml
skip_review:
  enabled: true                   # Enable skip detection
  skip_dependency_updates: true   # Skip dependency updates
  skip_documentation_only: false  # Skip doc-only changes (disabled by default)
  skip_bot_authors: true          # Skip known bots
  skip_draft_prs: true            # Skip draft/WIP PRs and MRs (enabled by default)

  # Built-in keywords (in PR/MR titles or descriptions)
  keywords:
    - "[skip review]"
    - "[no review]"
    - "[automated]"
    - "[bot]"

  # Built-in patterns (regex matching PR/MR titles)
  patterns:
    - "^(chore|build|ci|feat|fix)\\(deps?\\):"  # Dependency updates
    - "^(release|bump):"                        # Version bumps
    - "^(merge|revert):"                        # Merges and reverts
    - "^\\[automated\\]"                        # Automated changes

  # Documentation patterns (only used if skip_documentation_only: true)
  documentation_patterns:
    - "^docs?:"
    - "^doc\\(.*\\):"

  # Known bot accounts
  bot_authors:
    - "dependabot[bot]"
    - "renovate[bot]"
    - "github-actions[bot]"
    - "snyk-bot"
```

#### Customization Examples

**Disable Skip Review:**
```yaml
skip_review:
  enabled: false  # Disable all skip detection
```

**Custom Organization Patterns:**
```yaml
skip_review:
  enabled: true
  patterns:
    - "^\\[JIRA-\\d+\\] automated"     # JIRA automated tickets
    - "^hotfix/automated-"             # Automated hotfixes
    - "^chore\\(i18n\\):"              # Translation updates

  bot_authors:
    - "company-deploy-bot"
    - "security-scanner[bot]"

  keywords:
    - "[saltar revisión]"              # Spanish keywords
    - "[no revisar]"
```

**Enable Documentation-Only Skipping:**
```yaml
skip_review:
  enabled: true
  skip_documentation_only: true  # Enable doc-only detection
```

#### CLI Options

**Force review (ignore skip detection):**
```bash
# Force review even if it would normally be skipped
ai-code-review --no-skip-detection project/123
```

**Test skip detection without full review:**
```bash
# Test what the skip detection would do
ai-code-review --test-skip-only project/123

# Example output:
# 🧪 Testing skip detection logic...
# ✅ Review would be SKIPPED
#    Reason: pattern
#    Trigger: chore(deps):
#    Exit code would be: 6
```

#### CI/CD Integration

**Exit Codes:**
- `0` = Review completed successfully
- `6` = Review skipped (new exit code)
- Other codes = Errors

**GitLab CI - Handle Skip Review:**
```yaml
ai-review:
  stage: code-review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
  script:
    - ai-code-review --post
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

  # Allow exit code 6 (skipped) as success
  allow_failure:
    exit_codes: [6]
```

**GitHub Actions - Handle Skip Review:**
```yaml
- name: AI Code Review
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    AI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  run: ai-code-review --pr-number ${{ github.event.pull_request.number }} --post

  # Exit code 6 is handled as success automatically
```

**Environment Variables:**
```bash
# Disable via environment variable (overrides YAML config)
SKIP_REVIEW_ENABLED=false

# Force enable documentation-only skipping
SKIP_DOCUMENTATION_ONLY=true

# Disable specific features
SKIP_DEPENDENCY_UPDATES=false
SKIP_BOT_AUTHORS=false
SKIP_DRAFT_PRS=false  # Disable draft PR/MR skipping
```

#### Examples

**✅ These PRs/MRs get SKIPPED automatically:**

- `chore(deps): bump lodash from 4.1.0 to 4.2.0`
- `[automated] update translation files`
- `release: v2.1.0`
- `feat: new feature [skip review]`
- Author: `dependabot[bot]` with any title
- **Draft/WIP PRs and MRs** (enabled by default)
- Documentation-only changes (if enabled)

**❌ These PRs/MRs get REVIEWED normally:**

- `feat: implement new authentication system`
- `fix: resolve critical security vulnerability`
- Mixed changes (code + docs)
- Normal commits by human developers

**Benefits:**
- 🔇 **Less noise** - Focus on meaningful changes
- 💰 **Cost savings** - Fewer API calls to AI providers
- ⚡ **Faster CI/CD** - Skip unnecessary review steps
- 🎯 **Better focus** - Developers see only important reviews

#### SSL Configuration for Internal GitLab Instances

For internal GitLab instances using self-signed certificates or custom CA certificates:

**Option 1**: Automatic Certificate Download (Recommended):

```bash
# SSL Configuration - Automatic Download
SSL_VERIFY=true                                    # Enable SSL verification (recommended)
SSL_CERT_URL=https://gitlab.company.com/ca-bundle.crt  # URL to download certificate
SSL_CERT_CACHE_DIR=.ssl_cache                     # Cache directory (optional, defaults to .ssl_cache)
```

**Option 2**: Manual Certificate File:

```bash
# SSL Configuration - Manual Path
SSL_VERIFY=true                # Enable SSL verification (recommended)
SSL_CERT_PATH=/path/to/company-ca.crt  # Path to your company's CA certificate
```

**Option 3**: Development/Testing Only:

```bash
# Alternative for development/testing (NOT recommended for production)
SSL_VERIFY=false               # Disable SSL verification completely
```

##### Setting up SSL Certificates in CI/CD

###### Method 1: Automatic Download (Recommended)

Simply provide the URL where your certificate can be downloaded:

```yaml
ai-code-review:
  stage: code-review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
    # SSL configuration - automatic download
    SSL_VERIFY: "true"
    SSL_CERT_URL: "https://gitlab.company.com/ca-bundle.crt"  # Your internal CA certificate URL
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

###### Method 2: Upload Certificate File (Legacy)

1. **Upload your company's CA certificate** to your project:
   - **Settings** → **CI/CD** → **Variables**
   - Create a **File** variable named `COMPANY_CA_CERT`
   - Upload your `.crt` or `.pem` certificate file

2. **Configure the job to use the certificate:**

```yaml
ai-code-review:
  stage: code-review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
    # SSL configuration for internal GitLab
    SSL_VERIFY: "true"
    SSL_CERT_PATH: $COMPANY_CA_CERT  # References the uploaded certificate file
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

##### Quick setup for development environments

```yaml
ai-code-review:
  stage: code-review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
    # CAUTION: Only for development - disables SSL verification
    SSL_VERIFY: "false"
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Complete CI/CD Example

```yaml
stages:
  - test
  - code-review

# Your existing tests
test:
  stage: test
  script:
    - echo "Run your tests here"

# AI Code Review
ai-code-review:
  stage: code-review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
    LANGUAGE_HINT: python
    LOG_LEVEL: INFO
    # Exclude test files and docs from review
    EXCLUDE_PATTERNS: "**/*test*,docs/**,*.lock"
  script:
    # Optional: Health check first
    - ai-code-review --health-check
    # Generate and post review
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### 🎯 Project Context Configuration

Enhance AI review quality by providing project-specific context. The AI can give more targeted and relevant feedback when it understands your project's architecture, conventions, and goals.

> **📖 For complete context generator documentation** → see [Context Generator Guide](context-generator.md)

#### Setup Project Context

#### Recommended: Use the automatic context generator

```bash
# Generate comprehensive context automatically (requires Git repository)
ai-generate-context . --output .ai_review/project.md
```

> **Note**: The context generator analyzes only Git-tracked files. Make sure your project files are committed to Git.

**Manual alternative:** Create a context file manually:

```bash
mkdir -p .ai_review
# Create .ai_review/project.md with your project context
# See the ai-code-review project's .ai_review/project.md as a real example
```

**Customize** `.ai_review/project.md` with your project information:

```markdown
# Project Context for AI Code Review

## Project Overview
Web API for user management built with FastAPI and PostgreSQL.

## Technology Stack
- **Language:** Python 3.12+
- **Framework:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL
- **Testing:** pytest + httpx
- **Deployment:** Docker + Kubernetes

## Code Style & Guidelines
- **Style:** PEP 8 + Black formatting
- **Type Hints:** Mandatory with mypy validation
- **Async:** Use async/await for all I/O operations
- **Error Handling:** Custom exception classes with detailed messages

## Review Focus Areas
- **Security:** Validate all input parameters and SQL injection prevention
- **Performance:** Check for N+1 queries and proper async usage
- **API Design:** RESTful conventions and OpenAPI documentation
- **Testing:** Verify test coverage for new endpoints

## Common Issues & Gotchas
- **Intentional Patterns:** `# noqa` comments are legitimate for SQLAlchemy models
- **External Dependencies:** Redis client is injected via dependency injection container
- **Domain Logic:** Complex VAT calculations are required by EU regulations
- **Performance:** Deliberate caching in user service for authentication speed
```

1. **Control the feature** via environment variable or CLI flag:

```bash
# Environment variable (default: enabled if file exists)
ENABLE_PROJECT_CONTEXT=true/false

# CLI flags
ai-code-review --project-context project/123     # Enable explicitly
ai-code-review --no-project-context project/123  # Disable explicitly
ai-code-review --context-file docs/ai-context.md project/123  # Custom file path

# Output options
ai-code-review project/123 -o review.md          # Save to file
ai-code-review project/123 --output-file reports/review-$(date +%Y%m%d).md  # Timestamped file
```

#### Best Practices

- **Keep it concise**: AI has limited context window, focus on most important information
- **Update regularly**: Keep context current as your project evolves
- **Be specific**: Generic advice like "write good code" is less helpful than specific patterns
- **Include examples**: Show code examples for important conventions
- **Test the impact**: Compare reviews with and without context to measure improvement

### 👥 Team/Organization Context

For teams working on multiple projects, you can specify a **shared team context** that applies across all projects. This is perfect for organization-wide coding standards, security requirements, or team conventions that should be followed regardless of the specific project.

#### Use Cases

- **Organization Standards**: Shared coding conventions across all projects
- **Security Requirements**: Company-wide security policies and practices
- **Team Conventions**: Team-specific patterns and best practices
- **Compliance Guidelines**: Industry-specific requirements (e.g., HIPAA, GDPR)

#### Setup Team Context

**Option 1: Local Team Context File**

```bash
# Path to local team standards file
export TEAM_CONTEXT_FILE=../team-standards.md
ai-code-review --local

# Or use CLI option
ai-code-review group/project 123 --team-context ../team-standards.md --post
```

**Option 2: Remote Team Context (Recommended for Teams)**

Store your team context in a central repository accessible via URL:

```bash
# URL to team standards (e.g., from company GitLab/GitHub repo)
export TEAM_CONTEXT_FILE=https://gitlab.com/myorg/standards/-/raw/main/review-context.md
ai-code-review group/project 123 --post

# Or use CLI option
ai-code-review --local --team-context https://company.com/standards/review.md
```

**Example Team Context File:**

```markdown
# Organization Code Review Standards

## Security Requirements
- All API endpoints must have authentication
- Input validation mandatory for all user data
- No secrets in code - use environment variables
- SQL queries must use parameterized statements

## Code Quality Standards
- Test coverage minimum: 80%
- All functions must have type hints (Python/TypeScript)
- No commented-out code in production
- Error messages must be logged with context

## Performance Guidelines
- Database queries: avoid N+1 queries
- API response time target: < 200ms p95
- Use caching for expensive operations
- Optimize images before committing

## Team Conventions
- Branch naming: feature/*, bugfix/*, hotfix/*
- Commit messages: follow Conventional Commits
- PR size: keep under 400 lines when possible
- Reviews: approve only when all comments resolved
```

#### Priority Order

When multiple context sources are configured, they are applied in this priority order:

1. **Team/Organization Context** (highest priority) - Applied first
2. **Project Context** (`.ai_review/project.md`) - Applied second
3. **Commit History** - Applied last

This allows teams to maintain organization-wide standards while individual projects can add specific guidelines that complement (not override) the team standards.

#### Configuration Examples

**CLI:**
```bash
# Both team and project context
ai-code-review --team-context https://company.com/standards.md \
               --context-file .ai_review/project.md \
               group/project 123 --post
```

**Environment Variables:**
```bash
export TEAM_CONTEXT_FILE=https://gitlab.com/org/standards/-/raw/main/review.md
export ENABLE_PROJECT_CONTEXT=true  # Project context also enabled
ai-code-review group/project 123 --post
```

**YAML Configuration:**
```yaml
# .ai_review/config.yml
enable_project_context: true
team_context_file: https://gitlab.com/myorg/standards/-/raw/main/review-context.md
project_context_file: .ai_review/project.md
```

#### Best Practices

- **Keep team context general**: Focus on org-wide patterns, not project specifics
- **Use remote URLs**: Makes it easy to update standards across all projects
- **Version your standards**: Use Git tags or branches to version your team context
- **Combine with project context**: Team context for org standards, project context for specifics
- **Update centrally**: Changes to remote team context apply immediately to all projects

### 🧠 Intelligent Review Context (Two-Phase Synthesis)

The tool automatically learns from previous reviews to avoid repeating suggestions that were already addressed or invalidated by the PR/MR author. This feature uses a **two-phase approach** for optimal cost and quality.

#### How It Works

**Phase 1 - Synthesis (Automatic):**
1. Fetches **ALL** previous reviews and comments (including resolved ones)
2. Uses a fast, cheap model (e.g., `gemini-2.5-flash`) to synthesize key insights
3. Prioritizes author responses to previous AI reviews (**CRITICAL**)
4. Generates a concise summary (<500 words)

**Phase 2 - Main Review:**
1. Uses the synthesis as additional context
2. Main AI model generates review aware of previous discussions
3. Avoids repeating invalidated suggestions

#### Benefits

- ✅ **Prevents repeating mistakes** - AI knows what was already discussed
- ✅ **Respects author feedback** - Prioritizes author corrections to previous AI reviews
- ✅ **Reduces costs** - Synthesis uses cheap models (~1/10 cost of main model)
- ✅ **Better token efficiency** - 100s of comments → concise summary
- ✅ **Improves over time** - Each review cycle makes the AI smarter

#### Configuration

**Default behavior** (recommended):

```yaml
# Both features enabled by default
enable_review_context: true      # Fetch previous reviews/comments
enable_review_synthesis: true    # Use fast model for synthesis
```

**Custom synthesis model:**

```yaml
# Override default synthesis model (auto-selected per provider)
synthesis_model: gemini-2.5-flash         # For Gemini
# synthesis_model: claude-3-5-haiku-20241022  # For Anthropic
# synthesis_model: gpt-4o-mini              # For OpenAI

# Control synthesis output length
synthesis_max_tokens: 2000  # Default: 2000

# Limit comments fetched from API (performance optimization)
max_comments_to_fetch: 30  # Default: 30, increase for very active PRs
```

**Environment variables:**

```bash
# Enable/disable features
export ENABLE_REVIEW_CONTEXT=true
export ENABLE_REVIEW_SYNTHESIS=true

# Custom synthesis model
export SYNTHESIS_MODEL=gemini-2.5-flash
export SYNTHESIS_MAX_TOKENS=2000

# Limit comments fetched (performance optimization)
export MAX_COMMENTS_TO_FETCH=30  # Increase for very active PRs
```

**CLI flags:**

```bash
# Disable synthesis (use raw comments instead)
ai-code-review group/project 123 --no-synthesis

# Disable review context entirely
ai-code-review group/project 123 --no-review-context
```

#### Default Synthesis Models

The tool automatically selects fast/cheap models for synthesis based on your AI provider:

| Provider   | Main Model (Example)        | Synthesis Model (Default)    | Cost Ratio |
|------------|----------------------------|------------------------------|------------|
| Gemini     | gemini-3-pro-preview       | gemini-2.5-flash            | ~1/10      |
| Anthropic  | claude-sonnet-4            | claude-3-5-haiku-20241022   | ~1/5       |
| OpenAI     | gpt-4                      | gpt-4o-mini                 | ~1/15      |
| Ollama     | qwen2.5-coder:7b           | qwen2.5-coder:7b (same)     | N/A        |

#### When It Activates

✅ **Automatically activates when:**
- Previous reviews or comments exist
- Both features are enabled (default)
- Running in GitHub/GitLab mode (not local)

⏭️ **Automatically skips when:**
- First review (no comments yet)
- Features are disabled
- Running in `--local` mode

#### Token Usage Example

**Without synthesis (raw comments):**
- 50 comments × 200 tokens avg = **10,000 tokens** added to main model
- Cost: 10K tokens × main model price

**With synthesis:**
- Phase 1: 10,000 tokens × flash price (~$0.0001/1K) = **$0.001**
- Phase 2: 500 synthesis tokens × main model price
- **Total savings: ~90%** of comment token costs

#### What Gets Synthesized

The synthesis focuses on:

1. **CRITICAL: Author Responses** - Any responses from the PR/MR author that correct, clarify, or invalidate previous AI suggestions
2. **Addressed Issues** - Problems that were raised and have been resolved
3. **Active Discussions** - Ongoing conversations that need attention
4. **Reviewer Consensus** - Points where multiple reviewers agree

#### Example Synthesis Output

```markdown
## Review Context and Previous Discussions

### CRITICAL Author Corrections
- Author clarified that `process_data()` intentionally uses synchronous I/O 
  because the external API doesn't support async (comment on utils.py:45)
- Author explained the TODO on line 123 is tracked in issue #456 and will 
  be addressed in next sprint

### Addressed Issues
- Memory leak in connection pool was fixed in commit abc123
- Type hints were added to all public functions per previous review

### Active Discussions
- Performance optimization of `calculate_metrics()` still under discussion
- Team considering migration to Pydantic v2 (not yet decided)

**Note:** The above synthesis helps avoid repeating suggestions about 
synchronous I/O or requesting type hints that were already added.
```

#### Best Practices

- ✅ **Leave it enabled** - Default settings work well for most projects
- ✅ **Review first synthesis** - Check the synthesis output in your first review to understand what the AI learned
- ✅ **Respond to AI comments** - Your responses help the AI understand what's valid/invalid
- ✅ **Monitor costs** - Track token usage to verify savings (should be ~90% reduction for comments)

#### Disable When

- ❌ **Local reviews** - Feature is automatic-disabled for `--local` mode
- ❌ **First review ever** - No comments to synthesize yet
- ❌ **Testing/debugging** - Use `--no-synthesis` to isolate issues
- ❌ **Limited API quotas** - Disable to reduce API calls (though synthesis saves tokens overall)

### 📝 Review Format Configuration

Control what sections are included in AI reviews to match your team's preferences.

#### MR Summary Section

By default, AI reviews include both an **MR Summary** (executive overview) and **Detailed Code Review** (technical analysis):

```markdown
## AI Code Review

### 📋 MR Summary
Brief overview of changes, impact, and risk level

### Detailed Code Review
Technical analysis of code changes

### ✅ Summary
Final assessment and recommendations
```

#### Code-Focused Reviews

For teams that prefer shorter, more focused reviews, you can skip the MR Summary section:

```bash
# Environment variable
INCLUDE_MR_SUMMARY=false

# CLI flag
ai-code-review group/project 123 --no-mr-summary --post
```

**Result:** Reviews contain only the detailed technical analysis without the executive summary.

#### When to Use Code-Focused Reviews

- ✅ **Large development teams** where reviews are already long
- ✅ **Experienced developers** who prefer direct technical feedback
- ✅ **CI/CD environments** with strict message length limits
- ✅ **Personal projects** where executive summaries aren't needed

#### Example CI/CD with Project Context

```yaml
ai-code-review:
  stage: code-review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
    LANGUAGE_HINT: python
    ENABLE_PROJECT_CONTEXT: "true"  # Explicitly enable (default: true if file exists)
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```
t

### Recommended Workflows

#### For Daily Development

```bash
# 1. Make your changes
git add .

# 2. Quick review before committing (fast with Ollama)
ai-code-review --local --ai-provider ollama

# 3. Fix issues, then commit
git commit -m "fix: apply AI review suggestions"
```

#### For Team Code Reviews

```bash
# 1. Set up tokens (one time)
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
export AI_API_KEY=your_gemini_key

# 2. Test configuration
ai-code-review group/project 123 --dry-run

# 3. Analyze MR/PR
ai-code-review group/project 123

# 4. Post review if helpful
ai-code-review group/project 123 --post
```

#### 3. Custom GitLab Instance

For private or internal GitLab instances:

```bash
# Basic custom GitLab URL
GITLAB_TOKEN=your_token \
AI_API_KEY=your_key \
ai-code-review --gitlab-url https://gitlab.company.com internal/project 456 --post
```

**For Internal GitLab with SSL Certificates:**

```bash
# Option 1: Using custom CA certificate file
GITLAB_TOKEN=your_token \
AI_API_KEY=your_key \
SSL_VERIFY=true \
SSL_CERT_PATH=/path/to/company-ca.crt \
ai-code-review --gitlab-url https://gitlab.company.com \
  internal/project 456 --post

# Option 2: Create .env file for repeated use
cat > .env << 'EOF'
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
GITLAB_URL=https://gitlab.company.com
AI_API_KEY=your_gemini_key
SSL_VERIFY=true
SSL_CERT_PATH=/path/to/company-ca.crt
EOF

# Then simply run:
ai-code-review internal/project 456 --post
```

**For Development/Testing (Disable SSL verification):**

⚠️ **CAUTION**: Only for development environments where security is not critical.

```bash
# Temporarily disable SSL verification
GITLAB_TOKEN=your_token \
AI_API_KEY=your_key \
SSL_VERIFY=false \
ai-code-review --gitlab-url https://gitlab.company.com \
  internal/project 456 --post

# Or with .env file
cat > .env << 'EOF'
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
GITLAB_URL=https://gitlab.company.com
AI_API_KEY=your_gemini_key
SSL_VERIFY=false
EOF

ai-code-review internal/project 456 --post
```

### Output Options

The tool provides flexible output options for different workflows:

#### Terminal Display (Default)

```bash
# Review displayed in terminal (stdout)
ai-code-review group/project 123

# Clean output - logs go to stderr, review to stdout
ai-code-review group/project 123 2>/dev/null  # Hide logs, show only review
```

#### Save to File

```bash
# Save review to file
ai-code-review group/project 123 -o review.md
ai-code-review group/project 123 --output-file reports/mr-123-review.md

# Timestamped files for continuous review
ai-code-review group/project 123 -o "reviews/mr-123-$(date +%Y%m%d_%H%M).md"

# Save review and keep logs visible
ai-code-review group/project 123 -o review.md
```

#### Combining with Redirection

```bash
# Logs to stderr, review to file - best of both worlds
ai-code-review group/project 123 -o review.md

# Logs to file, review to stdout (traditional)
ai-code-review group/project 123 2>logs.txt

# Everything to separate files
ai-code-review group/project 123 -o review.md 2>logs.txt
```

## 🔧 Timeout Configuration

### Diff Download Timeout

When reviewing changes from GitLab or GitHub, the tool downloads the complete diff to ensure all files are included. For very large repositories or slow networks, you may need to adjust the timeout:

```bash
# Environment variable
export AI_CODE_REVIEW_DIFF_DOWNLOAD_TIMEOUT=180  # 3 minutes (default: 120)
```

```yaml
# In .ai-code-review.yaml
diff_download_timeout: 180  # seconds
```

**When you might need this:**
- Very large repositories (1000+ files changed)
- Slow network connections
- Self-hosted instances with rate limiting

**Default timeout (120 seconds) is sufficient for most cases.**

**Local Git Client:**
The local Git client also benefits from pre-filtering improvements:
- Binary files detected by extension before reading
- Excluded patterns filtered before reading from disk
- More efficient processing of local changes

### Technical Details

**Pre-filtering Logic:**

1. **Binary Detection**: Files with extensions like `.png`, `.pdf`, `.zip`, etc. are skipped
2. **Pattern Matching**: Files matching `exclude_patterns` are skipped
3. **Streaming Parser**: Only relevant files are parsed and stored in memory

**Memory Usage Comparison:**

| Scenario | Without Pre-filtering | With Pre-filtering |
|----------|----------------------|-------------------|
| 100 files, 30 lockfiles | ~50MB peak | ~20MB peak |
| 500 files, 200 binaries | ~200MB peak | ~50MB peak |

**This is completely automatic - no user action required.**

## 🔧 Troubleshooting

### Common Issues

#### "GitLab token not configured"

```bash
# Solution for remote reviews: Set your GitLab token
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx

# OR: Use local reviews (no tokens needed!)
ai-code-review --local
```

#### "LOCAL platform requires running from within a git repository"

```bash
# Solution 1: Run from inside your git project
cd /path/to/your/git/project
ai-code-review --local

# Solution 2: Make sure Git is installed
# Fedora/CentOS/RHEL: sudo dnf install git-core
# Ubuntu/Debian: sudo apt install git
# macOS: brew install git
# Windows: Download from https://git-scm.com/
```

#### "AI provider not available"

```bash
# Check connectivity
ai-code-review --health-check

# For Ollama: Make sure server is running
ollama serve
ollama pull qwen2.5-coder:7b
```

#### "MR not found"

```bash
# Verify project path and MR number
ai-code-review --gitlab-url https://gitlab.com group/project 123
```

#### SSL Certificate Errors

**Error**: `SSL: CERTIFICATE_VERIFY_FAILED` or `certificate verify failed: self-signed certificate`

This occurs when connecting to internal GitLab instances with custom or self-signed certificates.

##### Solutions

1. **Use automatic certificate download (recommended):**

    ```bash
    # No manual download needed - certificate is downloaded automatically
    SSL_VERIFY=true SSL_CERT_URL=https://gitlab.company.com/ca-bundle.crt \
    ai-code-review --gitlab-url https://gitlab.company.com internal/project 456
    ```

1. **Use your company's CA certificate manually (legacy):**

    ```bash
    # Download your company's certificate first
    curl -k https://gitlab.company.com > company-ca.crt

    # Then use it
    SSL_VERIFY=true SSL_CERT_PATH=./company-ca.crt \
    ai-code-review --gitlab-url https://gitlab.company.com internal/project 456
    ```

1. **Temporarily disable SSL verification (development only):**

    ```bash
    # ⚠️ CAUTION: Only for development/testing
    SSL_VERIFY=false \
    ai-code-review --gitlab-url https://gitlab.company.com internal/project 456
    ```

1. **For CI/CD pipelines:**

    ```yaml
    # Add to your .gitlab-ci.yml
    ai-code-review:
    variables:
        SSL_VERIFY: "true"
        SSL_CERT_PATH: $COMPANY_CA_CERT  # Upload as File variable in CI/CD settings
    # ... rest of job configuration
    ```

##### Common certificate issues

- **Wrong certificate path**: Check the file exists and is readable
- **Certificate format**: Use `.crt` or `.pem` format
- **Permission issues**: Ensure the certificate file is readable by the process
- **Expired certificates**: Check certificate validity with `openssl x509 -in cert.crt -text -noout`

### Debug Mode

Enable detailed logging:

```bash
# Local debugging
LOG_LEVEL=DEBUG ai-code-review group/project 123

# CI/CD debugging (add to variables)
LOG_LEVEL: DEBUG
```

## 📚 More Information

- **Project Repository**: <https://gitlab.com/redhat/edge/ci-cd/ai-code-review>
- **Issues & Support**: <https://gitlab.com/redhat/edge/ci-cd/ai-code-review/-/issues>
- **Complete Documentation**: See `README.md` and `SPECS.md` in the repository
