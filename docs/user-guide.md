# User Guide: AI Code Review

Simple guide to get AI-powered code reviews for your **GitLab Merge Requests** and **GitHub Pull Requests**.

## 🚀 Quick Setup Options

### Option 1: GitLab CI/CD (Pre-built Container)

Add this job to your `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - review

ai-code-review:
  stage: review
  image: registry.gitlab.com/redhat/edge/ci-cd/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY   # Set as protected/masked variable
  script:
    - ai-code-review --platform gitlab --post
  allow_failure: true  # Don't block MRs if review fails
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Option 2: GitHub Actions (Using GitLab Container)

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

### Option 2: Build Your Own Container

Create your own container and publish to your registry:

#### 2.1. Use Project's Containerfile

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

#### 2.2. Build and Push

```bash
# Build container
podman build -t $CI_REGISTRY_IMAGE/ai-review:latest .

# Push to your registry
podman push $CI_REGISTRY_IMAGE/ai-review:latest
```

#### 2.3. Use in CI/CD

```yaml
ai-code-review:
  stage: review
  image: $CI_REGISTRY_IMAGE/ai-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Option 3: Install from Repository

Install directly from the repository in your CI job:

#### GitLab Installation

```yaml
ai-code-review:
  stage: review
  image: python:3.12-slim
  variables:
    AI_API_KEY: $GEMINI_API_KEY
  before_script:
    # Install from GitLab repository (not published on PyPI yet)
    - pip install git+https://gitlab.com/redhat/edge/ci-cd/ai-code-review.git
  script:
    - ai-code-review --platform gitlab --post
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
AI_MODEL=gemini-2.5-pro         # Model name (gemini-2.5-pro, claude-sonnet-4-20250514)
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
  stage: review
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
  stage: review
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
  stage: review
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
  - review

# Your existing tests
test:
  stage: test
  script:
    - echo "Run your tests here"

# AI Code Review
ai-code-review:
  stage: review
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

#### Setup Project Context

1. **Create the context file** in your repository root:

    ```bash
    mkdir -p .ai_review
    cp .ai_review/project.md.example .ai_review/project.md
    ```

1. **Customize** `.ai_review/project.md` with your project information:

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
  stage: review
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

## 💻 Local Usage

Use AI Code Review locally to analyze GitLab MRs.

### Prerequisites

```bash
# Install locally from GitLab repository (not published on PyPI yet)
pip install git+https://gitlab.com/redhat/edge/ci-cd/ai-code-review.git

# Required: GitLab Personal Access Token
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx

# Optional: AI provider (Gemini/Anthropic for production, Ollama for local)
export AI_API_KEY=your_gemini_api_key     # For Gemini
export AI_API_KEY=your_anthropic_api_key  # For Anthropic
# OR use Ollama (no API key needed)
```

### Local Usage Examples

#### 1. Review and Display Only

Analyze an MR and see the review output:

```bash
# Using Gemini (production quality)
AI_API_KEY=your_key ai-code-review group/project 123

# Using Anthropic Claude (production quality)
AI_API_KEY=your_key ai-code-review group/project 123 --provider anthropic

# Using Ollama (local, free)
ai-code-review group/project 123 --provider ollama

# With custom settings
ai-code-review group/project 123 \
  --language-hint python \
  --exclude-files "**/*test*" \
  --big-diffs

# Code-focused review (without MR Summary section)
ai-code-review group/project 123 --no-mr-summary
```

#### 2. Review and Post to GitLab

Generate review and post it as MR comment:

```bash
# Post review to GitLab MR
AI_API_KEY=your_key ai-code-review group/project 123 --post

# Post code-focused review (without MR Summary section)
AI_API_KEY=your_key ai-code-review group/project 123 --post --no-mr-summary

# With health check first (recommended)
AI_API_KEY=your_key ai-code-review --health-check && \
AI_API_KEY=your_key ai-code-review group/project 123 --post
```

#### 3. Custom GitLab Instance

For private or internal GitLab instances:

```bash
# Basic custom GitLab URL
GITLAB_TOKEN=your_token \
AI_API_KEY=your_key \
ai-code-review --gitlab-url https://gitlab.company.com \
  --project-id "internal/project" --mr-iid 456 --post
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

### Local Development Workflow

```bash
# 1. Set up environment
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
export AI_API_KEY=your_gemini_key

# 2. Test with dry-run (no API costs)
ai-code-review group/project 123 --dry-run

# 3. Generate review locally
ai-code-review group/project 123

# 4. If satisfied, post to GitLab
ai-code-review group/project 123 --post
```

## 🔧 Troubleshooting

### Common Issues

#### "GitLab token not configured"

```bash
# Solution: Set your GitLab token
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
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
